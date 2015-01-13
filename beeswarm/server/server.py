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
import sys
import os

import gevent
from gevent.pywsgi import WSGIServer
import zmq.green as zmq
from zmq.auth.ioloop import IOLoopAuthenticator
from zmq.auth.certs import load_certificate

import beeswarm
from beeswarm.shared.helpers import create_self_signed_cert, stop_if_not_write_workdir
from beeswarm.shared.asciify import asciify
from beeswarm.server.db.database_actor import DatabaseActor
from beeswarm.server.misc.config_actor import ConfigActor
from beeswarm.shared.message_enum import Messages
from beeswarm.server.db import database_setup
from beeswarm.shared.socket_enum import SocketNames


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
        reset_password = kwargs['reset_password']
        if 'clear_db' in kwargs:
            clear_sessions = kwargs['clear_db']
        else:
            clear_sessions = True

        if 'server_hostname' in kwargs:
            server_hostname = kwargs['server_hostname']
        else:
            server_hostname = None

        max_sessions = kwargs['max_sessions']
        start_webui = kwargs['start_webui']

        self.work_dir = work_dir
        self.config_file = os.path.join(work_dir, 'beeswarmcfg.json')

        if config is None:
            self.prepare_environment(work_dir, customize, server_hostname=server_hostname)
            with open(os.path.join(work_dir, self.config_file), 'r') as config_file:
                self.config = json.load(config_file, object_hook=asciify)
        else:
            self.config = config
        # list of all self-running (actor) objects that receive or send
        # messages on one or more zmq queues
        self.actors = []
        self.greenlets = []

        proxy_greenlet = gevent.spawn(self.message_proxy, work_dir)
        self.greenlets.append(proxy_greenlet)
        config_actor = ConfigActor(self.config_file, work_dir)
        config_actor.start()
        self.actors.append(config_actor)
        self.greenlets.append(config_actor)

        # make path in sqlite connection string absolute
        connection_string = self.config['sql']['connection_string']
        if connection_string.startswith('sqlite:///'):
            _, relative_path = os.path.split(connection_string)
            connection_string = 'sqlite:///{0}'.format(os.path.join(self.work_dir, relative_path))
        database_setup.setup_db(connection_string)
        database_actor = DatabaseActor(max_sessions, clear_sessions)
        database_actor.start()
        self.actors.append(database_actor)
        self.greenlets.append(database_actor)

        for g in self.greenlets:
            g.link_exception(self.on_exception)

        gevent.sleep()

        self.started = False

        if start_webui:
            from beeswarm.server.webapp import app

            self.app = app.app
            self.app.config['CERT_PATH'] = self.config['ssl']['certpath']
            app.ensure_admin_password(reset_password)
        else:
            self.app = None

    # distributes messages between external and internal receivers and senders
    def message_proxy(self, work_dir):
        """
        drone_data_inboud   is for data comming from drones
        drone_data_outbound is for commands to the drones, topic must either be a drone ID or all for sending
                            a broadcast message to all drones
        """
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
        drone_data_inbound = beeswarm.shared.zmq_context.socket(zmq.PULL)
        drone_data_inbound.curve_secretkey = server_secret
        drone_data_inbound.curve_publickey = server_public
        drone_data_inbound.curve_server = True
        drone_data_inbound.bind('tcp://*:{0}'.format(self.config['network']['zmq_port']))

        drone_data_outbound = beeswarm.shared.zmq_context.socket(zmq.PUB)
        drone_data_outbound.curve_secretkey = server_secret
        drone_data_outbound.curve_publickey = server_public
        drone_data_outbound.curve_server = True
        drone_data_outbound.bind('tcp://*:{0}'.format(self.config['network']['zmq_command_port']))

        # internal interfaces
        # all inbound session data from drones will be replayed on this socket
        drone_data_socket = beeswarm.shared.zmq_context.socket(zmq.PUB)
        drone_data_socket.bind(SocketNames.DRONE_DATA.value)

        # all commands received on this will be published on the external interface
        drone_command_socket = beeswarm.shared.zmq_context.socket(zmq.PULL)
        drone_command_socket.bind(SocketNames.DRONE_COMMANDS.value)

        poller = zmq.Poller()
        poller.register(drone_data_inbound, zmq.POLLIN)
        poller.register(drone_command_socket, zmq.POLLIN)
        while True:
            # .recv() gives no context switch - why not? using poller with timeout instead
            socks = dict(poller.poll(100))
            gevent.sleep()

            if drone_command_socket in socks and socks[drone_command_socket] == zmq.POLLIN:
                data = drone_command_socket.recv()
                drone_id, _ = data.split(' ', 1)
                logger.debug("Sending drone command to: {0}".format(drone_id))
                # pub socket takes care of filtering
                drone_data_outbound.send(data)
            elif drone_data_inbound in socks and socks[drone_data_inbound] == zmq.POLLIN:
                raw_msg = drone_data_inbound.recv()
                split_data = raw_msg.split(' ', 2)
                if len(split_data) == 3:
                    topic, drone_id, data = split_data
                else:
                    data = None
                    topic, drone_id, = split_data
                logger.debug("Received {0} message from {1}.".format(topic, drone_id))
                # relay message on internal socket
                drone_data_socket.send(raw_msg)

    def start(self):
        """
            Starts the BeeSwarm server.
        """
        self.started = True
        if self.app:
            web_port = self.config['network']['web_port']
            logger.info('Starting server listening on port {0}'.format(web_port))
            key_file = os.path.join(self.work_dir, 'server.key')
            cert_file = os.path.join(self.work_dir, 'server.crt')
            http_server = WSGIServer(('', web_port), self.app, keyfile=key_file, certfile=cert_file)
            http_server_greenlet = gevent.spawn(http_server.serve_forever)
            self.greenlets.append(http_server_greenlet)

        stop_if_not_write_workdir(self.work_dir)
        logger.info('Server started.')
        gevent.joinall(self.greenlets)

    def stop(self):
        self.started = False
        logging.info('Stopping server.')
        for g in self.greenlets:
            g.kill()

    def on_exception(self, dead_greenlet):
        logger.error('Stopping because {0} died: {1}'.format(dead_greenlet, dead_greenlet.exception))
        self.stop()
        sys.exit(1)

    def get_config(self, configfile):
        """
            Loads the configuration from the JSON file, and returns it.
        :param configfile: Path to the configuration file
        """
        with open(configfile) as config_file:
            config = json.load(config_file)
        return config

    def prepare_environment(self, work_dir, customize, server_hostname=None):

        config_file = self.config_file
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

            if not server_hostname:
                print ''
                print '* Communication between drones (honeypots and clients) and server *'
                print '* Please make sure that drones can always contact the Beeswarm server using the information that' \
                      ' you are about to enter. *'
                server_hostname = raw_input('IP or hostname of server: ')

            zmq_port = 5712
            zmq_command_port = 5713
            if customize:
                zmq_port_input = raw_input('TCP port for session data (default: 5712) : ')
                if zmq_port_input != '':
                    zmq_port = int(zmq_port)

                zmq_command_port_input = raw_input('TCP port for drone commands(default: 5713) : ')
                if zmq_command_port_input != '':
                    zmq_command_port = int(zmq_port)

            # tmp actor while initializing
            config_actor = ConfigActor(self.config_file, work_dir)
            config_actor.start()
            context = beeswarm.shared.zmq_context
            socket = context.socket(zmq.REQ)
            gevent.sleep()
            socket.connect(SocketNames.CONFIG_COMMANDS.value)
            socket.send('{0} {1}'.format(Messages.GET_ZMQ_KEYS.value, 'beeswarm_server'))
            result = socket.recv()
            if result.split(' ', 1)[0] == Messages.OK.value:
                result = json.loads(result.split(' ', 1)[1])
                zmq_public, zmq_private = (result['public_key'], result['private_key'])
            else:
                assert False

            sqlite_db = os.path.join(work_dir, 'beeswarm_sqlite.db')
            message_dict = {'network': {'zmq_server_public_key': zmq_public,
                                        'web_port': web_port,
                                        'zmq_port': zmq_port,
                                        'zmq_command_port': zmq_command_port,
                                        'server_host': server_hostname},
                            'sql': {
                                'connection_string': 'sqlite:///{0}'.format(sqlite_db)},
                            'ssl': {
                                'certpath': 'server.crt',
                                'keypath': 'server.key'
                            },
                            'general': {
                                'mode': 'server'
                            },
                            'bait_session_retain': 2,
                            'malicious_session_retain': 100,
                            'ignore_failed_bait_session': False}
            socket.send('{0} {1}'.format(Messages.SET_CONFIG_ITEM.value, json.dumps(message_dict)))
            socket.recv()
            config_actor.stop()
