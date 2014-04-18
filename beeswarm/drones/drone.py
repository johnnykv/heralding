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
from requests.exceptions import Timeout, ConnectionError
import gevent
from beeswarm.shared.asciify import asciify
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
                logger.info('Fetched {0} as external ip for Honeypot.'.format(self.honeypot_ip))
            except (Timeout, ConnectionError) as e:
                logger.warning('Could not fetch public ip: {0}'.format(e))
        else:
            self.ip = ''

    def start(self):
        """ Starts services. """
        self.command_listener_greenlet = gevent.spawn(self.command_listener)

        mode = None
        if self.config['general']['mode'] == '':
            logger.info('Drone has not been configured, awaiting configuration from Beeswarm server.')
        elif self.config['general']['mode'] == 'honeypot':
            mode = Honeypot
        elif self.config['general']['mode'] == 'client':
            mode = Client

        if mode:
            self.drone = mode(self.work_dir, self.config)
            self.drone_greenlet = gevent.spawn(self.drone)

        #drop_privileges()
        logger.info("Drone running.")
        gevent.joinall([self.command_listener_greenlet])

    def stop(self):
        """Stops services"""
        assert(False)

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
        socket.setsockopt(zmq.SUBSCRIBE, 'all')

        socket.connect(self.config['beeswarm_server']['zmq_command_url'])
        logger.debug('Connected to server on {0}'.format(self.config['beeswarm_server']['zmq_command_url']))
        while True:
            message = socket.recv()
            topic, messagedata = message.split(' ', 1)
            logger.debug('Received {0} message.'.format(topic))
            # TODO: dispatch message internally
