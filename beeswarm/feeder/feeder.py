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
from beeswarm.feeder.consumer import consumer

gevent.monkey.patch_all()

import ConfigParser
import os
import sys
import shutil

import beeswarm
from beeswarm.feeder.bees import clientbase
from beeswarm.feeder.models.session import BeeSession
from beeswarm.errors import ConfigNotFound
import logging
import urllib2

# TODO: Autodetect

logger = logging.getLogger(__name__)


class Feeder(object):
    def __init__(self, work_dir, config_file='feeder.cfg.dist'):

        self.config = ConfigParser.ConfigParser()
        self.run_flag = True
        if not os.path.exists(config_file):
            raise ConfigNotFound('Configuration file could not be found. ({0})'.format(config_file))

        self.config.read(config_file)

        BeeSession.feeder_id = self.config.get('general', 'feeder_id')

        if self.config.getboolean('public_ip', 'fetch_ip'):
            self.my_ip = urllib2.urlopen('http://api-sth01.exip.org/?call=ip').read()
            logging.info('Fetched {0} as my external ip.'.format(self.my_ip))
        else:
            self.my_ip = '127.0.0.1'

    def start(self):
        logging.info('Starting feeder.')

        targets = self.get_targets()

        sessions = {}

        #greenlet to consume and maintain data in sessions list
        self.sessions_consumer = consumer.Consumer(sessions, self.config)
        gevent.spawn(self.sessions_consumer.start_handling)

        honeybees = []
        for b in clientbase.ClientBase.__subclasses__():
            bee = b(sessions)
            honeybees.append(bee)
            logging.debug('Adding {0} as a honeybee'.format(bee.__class__.__name__))

        while self.run_flag:
            for bee in honeybees:
                class_name = bee.__class__.__name__
                if class_name in targets:
                    bee_info = targets[class_name]
                    gevent.spawn(bee.do_session, bee_info['login'], bee_info['password'],
                                 bee_info['server'], bee_info['port'], self.my_ip)
            gevent.sleep(60)

    def get_targets(self):
        enabled_bees = self.config.sections()
        #TODO: Needs to be correlated with hive
        # Maybe correlation can be done when the webapp initializes a new hive/feeder pair
        targets = {}
        for bee in enabled_bees:
            if bee.startswith('bee_'):
                bee_name = bee[4:]  # discard the 'bee_' prefix
                targets[bee_name] = list2dict(self.config.items(bee))
            else:
                targets[bee] = list2dict(self.config.items(bee))
        return targets

    def stop(self):
        self.run_flag = False
        self.sessions_consumer.stop_handling()
        logger.info('All clients stopped')
        sys.exit(0)

    @staticmethod
    def prepare_environment(work_dir):
        package_directory = os.path.dirname(os.path.abspath(beeswarm.__file__))

        config_file = os.path.join(work_dir, 'feeder.cfg.dist')
        if not os.path.isfile(config_file):
            logging.info('Copying configuration file to current directory.')
            shutil.copyfile(os.path.join(package_directory, 'feeder/feeder.cfg.dist'),
                                         os.path.join(work_dir, 'feeder.cfg.dist'))

def list2dict(list_of_options):
    """Transforms a list of 2 element tuples to a dictionary"""
    d = {}
    for key, value in list_of_options:
        d[key] = value
    return d
