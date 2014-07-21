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
import urllib2

import gevent
from gevent.greenlet import Greenlet
import gevent.monkey


gevent.monkey.patch_all()

from beeswarm.drones.client.consumer.consumer import Consumer
from beeswarm.drones.client.baits import clientbase
from beeswarm.drones.client.models.session import BaitSession
from beeswarm.drones.client.models.dispatcher import BaitDispatcher
from beeswarm.shared.asciify import asciify
from beeswarm.shared.helpers import drop_privileges
from beeswarm.shared.helpers import extract_keys

# Do not remove this import, it is used to autodetect the capabilities.

logger = logging.getLogger(__name__)


class Client(object):
    def __init__(self, work_dir, config):

        """
            Main class which runs Beeswarm in Client mode.

        :param work_dir: Working directory (usually the current working directory)
        :param config_arg: Beeswarm configuration dictionary.
        """
        self.run_flag = True
        # maps honeypot id to IP
        self.honeypot_map = {}

        with open('beeswarmcfg.json', 'r') as config_file:
            self.config = json.load(config_file, object_hook=asciify)

        # write ZMQ keys to files - as expected by pyzmq
        extract_keys(work_dir, config)

        BaitSession.client_id = self.config['general']['id']

        if self.config['general']['fetch_ip']:
            self.my_ip = urllib2.urlopen('http://api-sth01.exip.org/?call=ip').read()
            logger.info('Fetched {0} as my external ip.'.format(self.my_ip))
        else:
            self.my_ip = '127.0.0.1'

        self.dispatcher_greenlets = []

    def start(self):
        """
            Starts sending client bees to the configured Honeypot.
        """
        logger.info('Starting client.')

        sessions = {}

        # greenlet to consume and maintain data in sessions list
        self.sessions_consumer = Consumer(sessions, self.config, self.my_ip)
        gevent.spawn(self.sessions_consumer.start_handling)

        self.dispatcher_greenlets = []

        for honeypot_id, entry in self.config['baits'].items():
            for b in clientbase.ClientBase.__subclasses__():
                bait_name = b.__name__.lower()
                # if the bait has a entry in the config we consider the bait enabled
                if bait_name in entry:
                    bait_options = entry[bait_name]
                    #bait_session = b(sessions, bait_options)
                    dispatcher = BaitDispatcher(sessions, b, bait_options)
                    dispatcher.start()
                    self.dispatcher_greenlets.append(dispatcher)
                    logger.info('Adding {0} bait'.format(bait_name))
                    logger.debug('Bait added with options: {0}'.format(bait_options))

        drop_privileges()
        gevent.joinall(self.dispatcher_greenlets)

    def stop(self):
        """
            Stop sending bait sessions.
        """
        for g in self.dispatcher_greenlets:
            g.kill()
        self.sessions_consumer.stop_handling()
        logger.info('All clients stopped')
