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
import os
import sys
import logging
import urllib2

import requests
import gevent
from gevent.greenlet import Greenlet
import gevent.monkey
gevent.monkey.patch_all()

from beeswarm.feeder.bees import clientbase
from beeswarm.feeder.models.session import BeeSession
from beeswarm.errors import ConfigNotFound
from beeswarm.feeder.models.dispatcher import BeeDispatcher
from beeswarm.shared.helpers import is_url
from beeswarm.shared.asciify import asciify
from beeswarm.shared.helpers import drop_privileges
from beeswarm.feeder.consumer import consumer

# Do not remove this import, it is used to autodetect the bees.
import beeswarm.feeder.bees

logger = logging.getLogger(__name__)


class Feeder(object):
    def __init__(self, work_dir, config_arg='feedercfg.json'):

        self.run_flag = True

        if not is_url(config_arg):
            if not os.path.exists(config_arg):
                raise ConfigNotFound('Configuration file could not be found. ({0})'.format(config_arg))
            try:
                with open(config_arg, 'r') as cfg:
                    self.config = json.load(cfg, object_hook=asciify)
            except (ValueError, TypeError) as e:
                raise Exception('Bad syntax for Config File: (%s)%s' % (e, str(type(e))))
        else:
            conf = requests.get(config_arg, verify=False)
            with open('feedercfg.json', 'w') as local_config:
                local_config.write(conf.text)
            self.config = json.loads(conf.text, object_hook=asciify)

        BeeSession.feeder_id = self.config['general']['feeder_id']
        BeeSession.hive_id = self.config['general']['hive_id']

        if self.config['public_ip']['fetch_ip']:
            self.my_ip = urllib2.urlopen('http://api-sth01.exip.org/?call=ip').read()
            logging.info('Fetched {0} as my external ip.'.format(self.my_ip))
        else:
            self.my_ip = '127.0.0.1'
        self.dispatchers = {}
        self.dispatcher_greenlets = []

    def start(self):
        logging.info('Starting feeder.')

        sessions = {}

        #greenlet to consume and maintain data in sessions list
        self.sessions_consumer = consumer.Consumer(sessions, self.config)
        gevent.spawn(self.sessions_consumer.start_handling)

        honeybees = []
        for b in clientbase.ClientBase.__subclasses__():
            bee_name = b.__name__

            if bee_name not in self.config['honeybees']:
                logger.warning(
                    "Not loading {0} bee because it has no option in configuration file.".format(b.__name__))
                continue
                #skip loading if disabled
            if not self.config['honeybees'][bee_name]['enabled']:
                logger.warning(
                    "Not loading {0} bee because it is disabled in the configuration file.".format(b.__name__))
                continue

            options = self.config['honeybees'][bee_name]
            bee = b(sessions, options)
            honeybees.append(bee)
            logging.debug('Adding {0} as a honeybee'.format(bee.__class__.__name__))

        self.dispatcher_greenlets = []
        for bee in honeybees:
            dispatcher = BeeDispatcher(self.config, bee, self.my_ip)
            self.dispatchers[bee.__class__.__name__] = dispatcher
            current_greenlet = Greenlet(dispatcher.start)
            self.dispatcher_greenlets.append(current_greenlet)
            current_greenlet.start()

        drop_privileges()
        gevent.joinall(self.dispatcher_greenlets)

    def stop(self):
        for g in self.dispatcher_greenlets:
            g.kill()
        self.sessions_consumer.stop_handling()
        logger.info('All clients stopped')
        sys.exit(0)
