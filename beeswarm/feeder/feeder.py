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

import gevent
import gevent.monkey
from beeswarm.feeder.consumer import consumer

gevent.monkey.patch_all()

import os
import sys
import shutil

import beeswarm
from beeswarm.feeder.bees import clientbase
from beeswarm.feeder.models.session import BeeSession
from beeswarm.errors import ConfigNotFound
from beeswarm.shared.helpers import asciify
import logging
import urllib2

# Do not remove this import, it is used to autodetect the bees.
import beeswarm.feeder.bees

logger = logging.getLogger(__name__)


class Feeder(object):
    def __init__(self, work_dir, config_arg='feedercfg.json'):

        self.run_flag = True
        if not os.path.exists(config_arg):
            raise ConfigNotFound('Configuration file could not be found. ({0})'.format(config_arg))

        try:
            with open(config_arg, 'r') as cfg:
                self.config = json.load(cfg, object_hook=asciify)
        except (ValueError, TypeError) as e:
            raise Exception('Bad syntax for Config File: (%s)%s' % (e, str(type(e))))

        BeeSession.feeder_id = self.config['general']['feeder_id']
        BeeSession.hive_id = self.config['general']['hive_id']

        if self.config['public_ip']['fetch_ip']:
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
        enabled_bees = self.config.keys()
        #TODO: Needs to be correlated with hive
        # Maybe correlation can be done when the webapp initializes a new hive/feeder pair
        targets = {}
        for bee in enabled_bees:
            if bee.startswith('bee_'):
                bee_name = bee[4:]  # discard the 'bee_' prefix
                targets[bee_name] = self.config[bee]
            else:
                targets[bee] = self.config[bee]
        return targets

    def stop(self):
        self.run_flag = False
        self.sessions_consumer.stop_handling()
        logger.info('All clients stopped')
        sys.exit(0)

    @staticmethod
    def prepare_environment(work_dir):
        package_directory = os.path.dirname(os.path.abspath(beeswarm.__file__))

        config_file = os.path.join(work_dir, 'feedercfg.json.dist')
        if not os.path.isfile(config_file):
            logging.info('Copying configuration file to current directory.')
            shutil.copyfile(os.path.join(package_directory, 'feeder/feedercfg.json.dist'),
                            os.path.join(work_dir, 'feedercfg.json'))