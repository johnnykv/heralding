# Copyright (C) 2013 Johnny Vestergaard <jkv@unixcluster.dk>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json
import logging
import os
from datetime import datetime

import gevent
from gevent.pywsgi import WSGIServer
import zmq.green as zmq
from zmq.auth.ioloop import IOLoopAuthenticator
from zmq.auth.certs import load_certificate

import beeswarm
from beeswarm.server.webapp import app
from beeswarm.server.webapp.auth import Authenticator
from beeswarm.shared.helpers import drop_privileges, send_zmq_request
from beeswarm.server.misc.scheduler import Scheduler
from beeswarm.shared.helpers import find_offset, create_self_signed_cert, generate_cert_digest
from beeswarm.shared.asciify import asciify
from beeswarm.server.db.session_persister import SessionPersister
from beeswarm.server.misc.config_actor import ConfigActor
from beeswarm.shared.message_enum import Messages
from beeswarm.server.db import database_setup
from beeswarm.server.db.entities import Drone


logger = logging.getLogger(__name__)


class Server(object):
    def __init__(self, work_dir, config, **kwargs):
        """
            Main class for the Web-Interface. It takes care of setting up
            the database, managing the users, etc.

        :param work_dir: The working directory (usually the current working directory).
        :param config_arg: Beeswarm configuration dictionary, None if not configuration was supplied.
        """
        customize = kwargs['customize']

        self.work_dir = work_dir
        self.config_file = 'beeswarmcfg.json'

        if config is None:
            Server.prepare_environment(work_dir, customize)
            with open(os.path.join(work_dir, self.config_file), 'r') as config_file:
                self.config = json.load(config_file, object_hook=asciify)
        else:
            self.config = config

        # list of all self-running (actor) objects that receive or send
        # messages on one or more zmq queues
        self.actors = []

        config_actor = ConfigActor(self.config_file, work_dir)
        config_actor.start()
        self.actors.append(config_actor)

        persistanceActor = SessionPersister()
        persistanceActor.start()
        self.actors.append(persistanceActor)

        self.workers = {}
        self.greenlets = []
        self.started = False

        database_setup.setup_db(os.path.join(self.config['sql']['connection_string']))
        self.app = app.app
        self.app.config['CERT_PATH'] = self.config['ssl']['certpath']
        self.app.config['SERVER_CONFIG'] = self.config_file
        self.authenticator = Authenticator()
        self.authenticator.ensure_default_user()
        gevent.spawn(self.message_proxy, work_dir)
        gevent.sleep()

    # distributes messages between external and internal receivers and senders
    def message_proxy(self, work_dir):
        """
        drone_data_inboud   is for data comming from drones
        drone_data_outbound is for commands to the drones, topic must either be a drone ID or all for sending
                            a broadcast message to all drones
        """
        ctx = zmq.Context()

        public_keys_dir = os.path.join(work_dir, 'certificates', 'public_keys')
        secret_keys_dir = os.path.join(work_dir, 'certificates', 'private_keys')

        # start and configure auth worker
        auth = IOLoopAuthenticator()
        auth.start()
        auth.allow('127.0.0.1')
        auth.configure_curve(domain='*', location=public_keys_dir)


        # external interfaces for communicating with drones
        server_secret_file = os.path.join(secret_keys_dir, 'beeswarm_server.pri')
        server_public, server_secret = load_certificate(server_secret_file)
        drone_data_inbound = ctx.socket(zmq.PULL)
        drone_data_inbound.curve_secretkey = server_secret
        drone_data_inbound.curve_publickey = server_public
        drone_data_inbound.curve_server = True
        drone_data_inbound.bind('tcp://*:{0}'.format(self.config['network']['zmq_port']))

        drone_data_outbound = ctx.socket(zmq.PUB)
        drone_data_outbound.curve_secretkey = server_secret
        drone_data_outbound.curve_publickey = server_public
        drone_data_outbound.curve_server = True
        drone_data_outbound.bind('tcp://*:{0}'.format(self.config['network']['zmq_command_port']))

        # internal interfaces
        # all inbound session data from drones will be replayed in this socket
        sessionPublisher = ctx.socket(zmq.PUB)
        sessionPublisher.bind('ipc://sessionPublisher')

        # all commands received on this will be published on the external interface
        drone_command_receiver = ctx.socket(zmq.PULL)
        drone_command_receiver.bind('ipc://droneCommandReceiver')

        poller = zmq.Poller()
        poller.register(drone_data_inbound, zmq.POLLIN)
        poller.register(drone_command_receiver, zmq.POLLIN)
        while True:
            # .recv() gives no context switch - why not? using poller with timeout instead
            socks = dict(poller.poll(100))
            gevent.sleep()

            if drone_command_receiver in socks and socks[drone_command_receiver] == zmq.POLLIN:
                data = drone_command_receiver.recv()
                drone_id, _ = data.split(' ', 1)
                logger.debug("Sending drone command to: {0}".format(drone_id))
                # pub socket takes care of filtering
                drone_data_outbound.send(data)
            elif drone_data_inbound in socks and socks[drone_data_inbound] == zmq.POLLIN:
                split_data = drone_data_inbound.recv().split(' ', 2)
                if len(split_data) == 3:
                    topic, drone_id, data = split_data
                else:
                    data = None
                    topic, drone_id, = split_data
                logger.debug("Received {0} message from {1}.".format(topic, drone_id))
                db_session = database_setup.get_session()
                drone = db_session.query(Drone).filter(Drone.id == drone_id).one()
                drone.last_activity = datetime.now()
                db_session.add(drone)
                db_session.commit()

                if topic == Messages.SESSION_HONEYPOT or topic == Messages.SESSION_CLIENT:
                    sessionPublisher.send('{0} {1}'.format(topic, data))
                elif topic == Messages.KEY or topic == Messages.CERT:
                    # for now we just store the fingerprint
                    # in the future it might be relevant to store the entire public key and private key
                    # for forensic purposes
                    if topic == Messages.CERT:
                        cert = data.split(' ', 1)[1]
                        digest = generate_cert_digest(cert)
                        logging.debug('Storing public key digest: {0} for drone {1}.'.format(digest, drone_id))
                        db_session = database_setup.get_session()
                        drone = db_session.query(Drone).filter(Drone.id == drone_id).one()
                        drone.cert_digest = digest
                        db_session.add(drone)
                        db_session.commit()
                elif topic == Messages.PING:
                    pass
                elif topic == Messages.IP:
                    ip_address = data
                    logging.debug('Drone {0} reported ip: {1}'.format(drone_id, ip_address))
                    db_session = database_setup.get_session()
                    drone = db_session.query(Drone).filter(Drone.id == drone_id).one()
                    drone.ip_address = ip_address
                    db_session.add(drone)
                    db_session.commit()
                # drons want it's config transmitted
                elif topic == Messages.DRONE_CONFIG:
                    config_dict = send_zmq_request('ipc://configCommands', '{0} {1}'.format(Messages.DRONE_CONFIG,
                                                                                            drone_id))
                    drone_data_outbound.send('{0} {1} {2}'.format(drone_id, Messages.CONFIG, json.dumps(config_dict)))
                else:
                    logger.warn('Message with unknown topic received: {0}'.format(topic))

    def start(self, maintenance=True):
        """
            Starts the BeeSwarm server.

        :param port: The port on which the web-app is to run.
        """
        self.started = True
        web_port = self.config['network']['web_port']
        logger.info('Starting server listening on port {0}'.format(web_port))
        http_server = WSGIServer(('', web_port), self.app, keyfile='server.key', certfile='server.crt')
        http_server_greenlet = gevent.spawn(http_server.serve_forever)
        self.workers['http'] = http_server
        self.greenlets.append(http_server_greenlet)

        if maintenance:
            maintenance_greenlet = gevent.spawn(self.start_maintenance_tasks)
            self.workers['maintenance'] = maintenance_greenlet
            self.greenlets.append(maintenance_greenlet)

        drop_privileges()
        logger.info('Server started and priviliges dropped.')
        gevent.joinall(self.greenlets)

    def stop(self):
        self.started = False
        logging.info('Stopping server.')
        self.workers['http'].stop(5)

    def get_config(self, configfile):
        """
            Loads the configuration from the JSON file, and returns it.
        :param configfile: Path to the configuration file
        """
        with open(configfile) as config_file:
            config = json.load(config_file)
        return config

    def start_maintenance_tasks(self):

        maintenance_worker = Scheduler(self.config)
        maintenance_greenlet = gevent.spawn(maintenance_worker.start)

        config_last_modified = os.stat(self.config_file).st_mtime
        while self.started:
            poll_last_modified = os.stat(self.config_file).st_mtime
            if poll_last_modified > config_last_modified:
                logger.debug('Config file changed, restarting maintenance workers.')
                config_last_modified = poll_last_modified
                config = self.get_config(self.config_file)

                # kill and stop old greenlet
                maintenance_worker.stop()
                maintenance_greenlet.kill(timeout=2)

                # spawn new worker greenlet and pass the new config
                maintenance_worker = Scheduler(config)
                maintenance_greenlet = gevent.spawn(maintenance_worker.start)

            # check config file for changes every 5 second
            gevent.sleep(5)

    @staticmethod
    def prepare_environment(work_dir, customize):
        package_directory = os.path.dirname(os.path.abspath(beeswarm.__file__))
        config_file = os.path.join(work_dir, 'beeswarmcfg.json')

        if not os.path.isfile(config_file):
            print '*** Please answer a few configuration options ***'
            if customize:
                logging.info('Copying configuration file to workdir.')
                print ''
                print '* Certificate Information *'
                print 'IMPORTANT: Please make sure that "Common Name" is the IP address or fully qualified host name ' \
                      ' that you want to use for the server API.'
                cert_cn = raw_input('Common Name: ')
                cert_country = raw_input('Country: ')
                cert_state = raw_input('State: ')
                cert_locality = raw_input('Locality/City: ')
                cert_org = raw_input('Organization: ')
                cert_org_unit = raw_input('Organizational unit: ')
                print ''
                print '* Network *'
                web_port = raw_input('Port for UI (default: 5000): ')
                if web_port:
                    web_port = int(web_port)
                else:
                    web_port = 5000
            else:
                logging.warn('Beeswarm server will be configured using default ssl parameters and network '
                             'configuration, this could be used to fingerprint the beeswarm server. If you want to '
                             'customize these options please use the --customize options on first startup.')
                cert_cn = '*'
                cert_country = 'US'
                cert_state = 'None'
                cert_locality = 'None'
                cert_org = 'None'
                cert_org_unit = ''
                web_port = 5000

            cert, priv_key = create_self_signed_cert(cert_country, cert_state, cert_org, cert_locality, cert_org_unit,
                                                     cert_cn)

            cert_path = os.path.join(work_dir, 'server.crt')
            key_path = os.path.join(work_dir, 'server.key')
            with open(cert_path, 'w') as certfile:
                certfile.write(cert)
            with open(key_path, 'w') as keyfile:
                keyfile.write(priv_key)

            print ''
            print '* Communication between drones (honeypots and clients) and server *'
            print '* Please make sure that drones can always contact the Beeswarm server using the information that' \
                  ' you are about to enter. *'

            zmq_port = 5712
            zmq_command_port = 5713
            server_hostname = raw_input('IP or hostname of server: ')
            if customize:
                zmq_port = raw_input('TCP port for session data (default: 5712) : ')
                if zmq_port != '':
                    zmq_port = int(zmq_port)

                zmq_command_port = raw_input('TCP port for drone commands(default: 5713) : ')
                if zmq_command_port != '':
                    zmq_command_port = int(zmq_port)

            # tmp actor while initializing
            config_actor = ConfigActor('beeswarmcfg.json', work_dir)
            config_actor.start()

            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.connect('ipc://configCommands')
            socket.send('{0} {1}'.format(Messages.GEN_ZMQ_KEYS, 'beeswarm_server'))
            result = socket.recv()
            if result.split(' ', 1)[0] == Messages.OK:
                result = json.loads(result.split(' ', 1)[1])
                zmq_public, zmq_private = (result['public_key'], result['private_key'])
            else:
                assert False

            socket.send('{0} {1}'.format(Messages.SET, json.dumps({'network': {'zmq_server_public_key': zmq_public,
                                                                               'web_port': web_port,
                                                                               'zmq_port': zmq_port,
                                                                               'zmq_command_port': zmq_command_port,
                                                                               'server_host': server_hostname},
                                                                   'sql': {
                                                                       'connection_string': 'sqlite:///beeswarm_sqlite.db'},
                                                                   'ssl': {
                                                                       'certpath': 'server.crt',
                                                                       'keypath': 'server.key'
                                                                   },
                                                                   'general': {
                                                                       'mode': 'server'
                                                                   },
                                                                   'bait_session_retain': 2,
                                                                   'malicious_session_retain': 100,
                                                                   'ignore_failed_bait_session': False


            }
            )))

            socket.recv()
            config_actor.close()
