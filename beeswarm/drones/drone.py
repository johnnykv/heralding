# Copyright (C) 2014 Johnny Vestergaard <jkv@unixcluster.dk>
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

import os
import logging
import requests
import json
from requests.exceptions import Timeout, ConnectionError
import gevent
from beeswarm.shared.asciify import asciify
from beeswarm.shared.message_enum import Messages
from beeswarm.shared.helpers import extract_keys
from beeswarm.drones.honeypot.honeypot import Honeypot
from beeswarm.drones.client.client import Client
import zmq.green as zmq
import zmq.auth

logger = logging.getLogger(__name__)


class Drone(object):

    """ Aggregates a honeypot or client. """

    def __init__(self, work_dir, config, key='server.key', cert='server.crt', curses_screen=None):
        """

        :param work_dir: Working directory (usually the current working directory)
        :param config: Beeswarm configuration dictionary, None if no configuration was supplied.
        :param key: Key file used for SSL enabled capabilities
        :param cert: Cert file used for SSL enabled capabilities
        :param curses_screen: Contains a curses screen object, if UI is enabled. Default is None.
        """

        # write ZMQ keys to files - as expected by pyzmq
        extract_keys(work_dir, config)
        self.work_dir = work_dir
        self.config = config
        self.key = key
        self.cert = cert
        self.id = self.config['general']['id']

        # Honeypot / Client
        self.drone = None
        self.drone_greenlet = None
        self.command_listener_greenlet = None

        if self.config['general']['fetch_ip']:
            try:
                url = 'http://api.externalip.net/ip'
                req = requests.get(url)
                self.ip = req.text
                logger.info('Fetched {0} as external ip for Honeypot.'.format(self.ip))
            except (Timeout, ConnectionError) as e:
                logger.warning('Could not fetch public ip: {0}'.format(e))
        else:
            self.ip = ''

    def start(self):
        """ Starts services. """
        self.command_listener_greenlet = gevent.spawn(self.command_listener)

        self._start_drone()

        #drop_privileges()
        logger.info('Drone running using id: {0}'.format(self.id))
        gevent.joinall([self.command_listener_greenlet])

    def _start_drone(self):
        """
        Tears down the drone if and restarts it.
        """

        mode = None
        if self.config['general']['mode'] == '':
            logger.info('Drone has not been configured, awaiting configuration from Beeswarm server.')
        elif self.config['general']['mode'] == 'honeypot':
            mode = Honeypot
        elif self.config['general']['mode'] == 'client':
            mode = Client

        if mode:
            self.drone = mode(self.work_dir, self.config)
            self.drone_greenlet = gevent.spawn(self.drone.start)

    def _stop_drone(self):
        """Stops services"""
        logging.debug('Stopping drone, hang on.')
        if self.drone is not None:
            self.drone.stop()
        # just some time for the drone to powerdown to be nice.
        gevent.sleep(2)
        if self.drone_greenlet is not None:
            self.drone_greenlet.kill(timeout=5)

    # command from server
    def command_listener(self):
        context = zmq.Context()
        socket = context.socket(zmq.SUB)

        cert_path = os.path.join(self.work_dir, 'certificates')
        public_keys_dir = os.path.join(cert_path, 'public_keys')
        private_keys_dir = os.path.join(cert_path, 'private_keys')

        client_secret_file = os.path.join(private_keys_dir, "client.key")
        client_public, client_secret = zmq.auth.load_certificate(client_secret_file)

        socket.curve_secretkey = client_secret
        socket.curve_publickey = client_public

        server_public_file = os.path.join(public_keys_dir, "server.key")
        server_public, _ = zmq.auth.load_certificate(server_public_file)

        socket.curve_serverkey = server_public
        socket.setsockopt(zmq.RECONNECT_IVL, 2000)
        # messages to this specific drone
        socket.setsockopt(zmq.SUBSCRIBE, self.id)
        # broadcasts to all drones
        socket.setsockopt(zmq.SUBSCRIBE, Messages.BROADCAST)

        socket.connect(self.config['beeswarm_server']['zmq_command_url'])
        logger.debug('Connected to server on {0}'.format(self.config['beeswarm_server']['zmq_command_url']))

        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)
        while True:
            # .recv() gives no context switch - why not? using poller with timeout instead
            socks = dict(poller.poll(1))
            gevent.sleep()

            if socket in socks and socks[socket] == zmq.POLLIN:
                message = socket.recv()
                # expected format for drone commands are:
                # DRONE_ID COMMAND OPTIONAL_DATA
                # DRONE_ID and COMMAND must not contain spaces
                drone_id, command, data = message.split(' ', 2)
                logger.debug('Received {0} command.'.format(command))
                assert(drone_id == self.id)
                #if we receive a configuration we restart the drone
                if command == Messages.CONFIG:
                    self.config = json.loads(data)
                    with open('beeswarmcfg.json', 'w') as local_config:
                        local_config.write(json.dumps(self.config, indent=4))
                    self._stop_drone()
                    self._start_drone()
                else:
                    # TODO: Dispatch the message using internal zmq
                    logger.warning('Unknown command received.')
                    pass
        logger.warn('Command listener exiting.')



