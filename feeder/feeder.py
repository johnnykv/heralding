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

import gevent
import gevent.monkey
gevent.monkey.patch_all()

import ConfigParser
import os

from bees import clientbase
from consumer import consumer
import logging
import urllib2

logger = logging.getLogger(__name__)


class Feeder(object):
    def __init__(self, config_file='feeder.cfg'):

        self.config = ConfigParser.ConfigParser()

        if not os.path.exists(config_file):
            raise ConfigNotFound('Configuration file could not be found. ({0})'.format(config_file))

        self.config.read(config_file)

        if self.config.getboolean('public_ip', 'fetch_ip'):
            self.my_ip = urllib2.urlopen('http://api-sth01.exip.org/?call=ip').read()
            logging.info('Fetched {0} as my external ip.'.format(self.my_ip))

    def start_feeding(self):
        logging.info('Starting feeder.')

        targets = self.get_targets()

        sessions = {}

        #greenlet to consume and maintain data in sessions list
        sessions_consumer = consumer.Consumer(sessions)
        gevent.spawn(sessions_consumer.start_handling)

        honeybees = []
        for b in clientbase.ClientBase.__subclasses__():
            bee = b(sessions)
            honeybees.append(bee)
            logging.debug('Adding {0}s as a honeybee'.format(bee.__class__.__name__))

        while True:
            for bee in honeybees:
                class_name = bee.__class__.__name__
                if class_name in targets:
                    bee_info = targets[class_name]
                    gevent.spawn(bee.do_session, bee_info['login'], bee_info['password'],
                                 bee_info['server'], bee_info['port'], self.my_ip)
            gevent.sleep(60)


    def get_targets(self):
        #TODO: Read from file or generate... Needs to be correlated with hive
        return {'pop3':
                    {'server': '127.0.0.1',
                     'port': 2100,
                     'timing': 'regular',
                     'login': 'test',
                     'password': 'test'}
        }

class ConfigNotFound(Exception):
    pass

