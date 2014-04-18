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
import shutil

import gevent
from gevent.pywsgi import WSGIServer
import zmq.green as zmq
from zmq.auth.ioloop import IOLoopAuthenticator
from zmq.auth.certs import load_certificate

import beeswarm
from beeswarm.server.db import database_setup
from beeswarm.server.webapp import app
from beeswarm.server.webapp.auth import Authenticator
from beeswarm.shared.helpers import drop_privileges
from beeswarm.server.misc.scheduler import Scheduler
from beeswarm.shared.helpers import find_offset, create_self_signed_cert, update_config_file, send_zmq_request
from beeswarm.shared.asciify import asciify
from beeswarm.server.db.session_persister import PersistanceWorker
from beeswarm.shared.workers.config_actor import ConfigActor

logger = logging.getLogger(__name__)


class Server(object):
    def __init__(self, work_dir, config, curses_screen=None):
        """
            Main class for the Web-Interface. It takes care of setting up
            the database, managing the users, etc.

        :param work_dir: The working directory (usually the current working directory).
        :param config_arg: Beeswarm configuration dictionary, None if not configuration was supplied.
        :param curses_screen: This parameter is to maintain a similar interface for
                               all the modes. It is ignored for the Server.
        """
        if config is None:
            Server.prepare_environment(work_dir)
            with open(os.path.join(work_dir, 'beeswarmcfg.json'), 'r') as config_file:
                config = json.load(config_file, object_hook=asciify)
        self.work_dir = work_dir
        self.config = config
        self.config_file = 'beeswarmcfg.json'

        self.actors = []
        config_actor = ConfigActor('beeswarmcfg.json', work_dir)
        config_actor.start()
        self.actors.append(config_actor)
        self.workers = {}
        self.greenlets = []
        self.started = False

        database_setup.setup_db(os.path.join(self.config['sql']['connection_string']))
        self.app = app.app
        self.app.config['CERT_PATH'] = self.config['ssl']['certpath']
        self.app.config['SERVER_CONFIG'] = 'beeswarmcfg.json'
        self.authenticator = Authenticator()
        self.authenticator.ensure_default_user()
        gevent.spawn(self.message_proxy, work_dir)
        persistanceWorker = PersistanceWorker()
        gevent.spawn(persistanceWorker.start)
        gevent.sleep()

    # distributes messages between external and internal receivers and senders
    def message_proxy(self, work_dir):
        """
        drone_data_inboud   is for data comming from drones
        drone_data_outbound is for commands to the drone, topic must either be a drone ID or all for sending
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
            socks = dict(poller.poll(5))
            gevent.sleep()

            if drone_command_receiver in socks and socks[drone_command_receiver] == zmq.POLLIN:
                data = drone_command_receiver.recv()
                topic, message = data.split(' ', 1)
                logger.debug("Sending drone command to: {0}".format(topic))
                # pub socket takes care of filtering
                drone_data_outbound.send(data)
            elif drone_data_inbound in socks and socks[drone_data_inbound] == zmq.POLLIN:
                topic, data = drone_data_inbound.recv().split(' ', 1)
                logger.debug("Received {0} data.".format(topic))
                if topic == 'session_honeypot' or topic == 'session_client':
                    sessionPublisher.send('{0} {1}'.format(topic, data))
                else:
                    logger.warn('Message with unknown topic received: {0}'.format(topic))

    def start(self, port=5000, maintenance=True):
        """
            Starts the BeeSwarm server.

        :param port: The port on which the web-app is to run.
        """
        self.started = True
        logger.info('Starting server listening on port {0}'.format(port))

        http_server = WSGIServer(('', 5000), self.app, keyfile='server.key', certfile='server.crt')
        http_server_greenlet = gevent.spawn(http_server.serve_forever)
        self.workers['http'] = http_server
        self.greenlets.append(http_server_greenlet)

        if maintenance:
            maintenance_greenlet = gevent.spawn(self.start_maintenance_tasks)
            self.workers['maintenance'] = maintenance_greenlet
            self.greenlets.append(maintenance_greenlet)

        drop_privileges()
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
        # one-off task to ensure we have the correct offset

        logger.info('Hang on, calculating binary offset - this can take a while!')
        if os.path.isfile(self.config['iso']['path']):
            config_tar_offset = find_offset(self.config['iso']['path'], '\x07' * 30)

            if not config_tar_offset:
                logger.warning('Beeswarm client ISO was found but is invalid. Bootable clients can not be generated.')
                raise Exception('Expected binary pattern not found in ISO file.')
            else:
                logger.debug('Binary pattern found in ISO at: {0}'.format(config_tar_offset))
                with open(self.config_file, 'r+') as config_file:
                    self.config['iso']['offset'] = config_tar_offset
                    #clear file
                    config_file.seek(0)
                    config_file.truncate(0)
                    # and  write again
                    config_file.write(json.dumps(self.config, indent=4))
        else:
            logger.warning('Beeswarm client ISO was NOT found. Bootable clients can not be generated.')

        maintenance_worker = Scheduler(self.config)
        maintenance_greenlet = gevent.spawn(maintenance_worker.start)

        config_last_modified = os.stat(self.config_file).st_mtime
        while self.started:
            poll_last_modified = os.stat(self.config_file).st_mtime
            if poll_last_modified > config_last_modified:
                logger.debug('Config file changed, restarting maintenance workers.')
                config_last_modified = poll_last_modified
                config = self.get_config(self.config_file)

                #kill and stop old greenlet
                maintenance_worker.stop()
                maintenance_greenlet.kill(timeout=2)

                #spawn new worker greenlet and pass the new config
                maintenance_worker = Scheduler(config)
                maintenance_greenlet = gevent.spawn(maintenance_worker.start)

            #check config file for changes every 5 second
            gevent.sleep(5)

    @staticmethod
    def prepare_environment(work_dir):
        package_directory = os.path.dirname(os.path.abspath(beeswarm.__file__))
        config_file = os.path.join(work_dir, 'beeswarmcfg.json')
        if not os.path.isfile(config_file):
            logging.info('Copying configuration file to workdir.')
            print '*** Please answer a few configuration options ***'
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
            tcp_port = raw_input('Port for UI (default: 5000): ')
            if tcp_port:
                tcp_port = int(tcp_port)
            else:
                tcp_port = 5000
            # to keep things simple we just use the CN for host for now.
            tcp_host = cert_cn

            create_self_signed_cert(work_dir, 'server.crt', 'server.key', cert_country, cert_state, cert_org,
                                    cert_locality, cert_org_unit, cert_cn)

            shutil.copyfile(os.path.join(package_directory, 'server/beeswarmcfg.json.dist'),
                            config_file)

            print ''
            print '* Communication between honeypots and server *'
            zmq_host = raw_input('IP or hostname of server: ')
            zmq_port = raw_input('TCP port for session data (default: 5712) : ')
            if zmq_port:
                zmq_port = int(zmq_port)
            else:
                zmq_port = 5712

            zmq_command_port = raw_input('TCP port for drone commands(default: 5713) : ')
            if zmq_command_port:
                zmq_command_port = int(zmq_port)
            else:
                zmq_command_port = 5713

            #tmp actor while initializing
            configActor = ConfigActor('beeswarmcfg.json', work_dir)
            configActor.start()

            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.connect('ipc://configCommands')
            socket.send('gen_zmq_keys beeswarm_server')
            result = socket.recv()
            if result.split(' ', 1)[0] == beeswarm.OK:
                result = json.loads(result.split(' ', 1)[1])
                zmq_public, zmq_private = (result['public_key'], result['private_key'])
            else:
                assert(False)

            socket.send('set {0}'.format(json.dumps({'network': {'zmq_server_public_key': zmq_public,
                                                                 'port': tcp_port, 'host': tcp_host,
                                                                 'zmq_port': zmq_port,
                                                                 'zmq_command_port': zmq_command_port,
                                                                 'zmq_host': zmq_host}})))
            socket.recv()
            configActor.close()
