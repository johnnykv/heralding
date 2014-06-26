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
import sys
import logging
import urllib2

import gevent
from gevent.greenlet import Greenlet
import gevent.monkey
from beeswarm.drones.client.consumer.consumer import Consumer
from beeswarm.shared.models.ui_handler import ClientUIHandler
import zmq.green as zmq

gevent.monkey.patch_all()

from beeswarm.drones.client.capabilities import clientbase
from beeswarm.drones.client.models.session import BaitSession
from beeswarm.drones.client.models.dispatcher import BeeDispatcher
from beeswarm.shared.asciify import asciify
from beeswarm.shared.helpers import drop_privileges
from beeswarm.shared.helpers import extract_keys
from beeswarm.shared.message_enum import Messages

# Do not remove this import, it is used to autodetect the capabilities.

logger = logging.getLogger(__name__)


class Client(object):
    def __init__(self, work_dir, config, curses_screen=None):

        """
            Main class which runs Beeswarm in Client mode.

        :param work_dir: Working directory (usually the current working directory)
        :param config_arg: Beeswarm configuration dictionary.
        :param curses_screen: Contains a curses screen object, if UI is enabled. Default is None.
        """
        self.run_flag = True
        self.curses_screen = curses_screen
        # maps honeypot id to IP
        self.honeypot_map = {}

        with open('beeswarmcfg.json', 'r') as config_file:
            self.config = json.load(config_file, object_hook=asciify)

        # write ZMQ keys to files - as expected by pyzmq
        extract_keys(work_dir, config)

        BaitSession.client_id = self.config['general']['id']
        # TODO: Handle peering in other place
        BaitSession.honeypot_id = self.config['general']['id']

        if self.config['general']['fetch_ip']:
            self.my_ip = urllib2.urlopen('http://api-sth01.exip.org/?call=ip').read()
            logger.info('Fetched {0} as my external ip.'.format(self.my_ip))
        else:
            self.my_ip = '127.0.0.1'

        self.status = {
            'mode': 'Client',
            'total_bees': 0,
            'active_bees': 0,
            'enabled_bees': [],
            'id': self.config['general']['id'],
            'ip_address': self.my_ip
        }

        self.dispatchers = {}
        self.dispatcher_greenlets = []

        if self.curses_screen is not None:
            self.uihandler = ClientUIHandler(self.status, self.curses_screen)
            Greenlet.spawn(self.show_status_ui)

    def show_status_ui(self):
        self.uihandler.run()

    def start(self):
        """
            Starts sending client bees to the configured Honeypot.
        """
        logger.info('Starting client.')

        sessions = {}

        #greenlet to consume and maintain data in sessions list
        self.sessions_consumer = Consumer(sessions, self.config, self.status)
        gevent.spawn(self.sessions_consumer.start_handling)

        capabilities = []
        for b in clientbase.ClientBase.__subclasses__():
            capability_name = b.__name__.lower()

            if capability_name not in self.config['capabilities']:
                logger.warning(
                    "Not loading {0} capability because it has no option in configuration file.".format(b.__name__))
                continue
                #skip loading if disabled
            if not self.config['capabilities'][capability_name]['enabled']:
                logger.warning(
                    "Not loading {0} capability because it is disabled in the configuration file.".format(b.__name__))
                continue

            options = self.config['capabilities'][capability_name]
            bait_session = b(sessions, options)
            capabilities.append(bait_session)
            self.status['enabled_bees'].append(capability_name)
            logger.debug('Adding {0} as a capability'.format(bait_session.__class__.__name__))

        self.dispatcher_greenlets = []
        for bait_session in capabilities:
            dispatcher = BeeDispatcher(self.config, bait_session, self.my_ip)
            self.dispatchers[bait_session.__class__.__name__] = dispatcher
            current_greenlet = Greenlet(dispatcher.start)
            self.dispatcher_greenlets.append(current_greenlet)
            current_greenlet.start()

        drop_privileges()
        gevent.joinall(self.dispatcher_greenlets)

    def stop(self):
        """
            Stop sending bait sessions.
        """
        for g in self.dispatcher_greenlets:
            g.kill()
        if self.curses_screen is not None:
            self.uihandler.stop()
        self.sessions_consumer.stop_handling()
        logger.info('All clients stopped')

    def server_command_listener(self):
        ctx = zmq.Context()
        client_command_receiver = ctx.socket(zmq.PULL)
        client_command_receiver.bind('ipc://serverRelay')

        poller = zmq.Poller()
        poller.register(client_command_receiver, zmq.POLLIN)

        while True:
            # .recv() gives no context switch - why not? using poller with timeout instead
            socks = dict(poller.poll(1))
            gevent.sleep()
            if client_command_receiver in socks and socks[client_command_receiver] == zmq.POLLIN:
                topic, data = client_command_receiver.recv().split(' ', 1)
                logger.debug("Received {0} data.".format(topic))
                if topic == Messages.IP:
                    honeypot_id, ip_address = data.split(' ')
                    self.honeypot_map[honeypot_id, ip_address]