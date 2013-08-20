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

import gevent
from gevent.pywsgi import WSGIServer
from beeswarm.beekeeper.db import database
from beeswarm.beekeeper.webapp import app
from beeswarm.beekeeper.webapp.auth import Authenticator
from beeswarm.shared.helpers import drop_privileges
from beeswarm.beekeeper.misc.scheduler import Scheduler

logger = logging.getLogger(__name__)


class Beekeeper(object):
    def __init__(self, work_dir, config_arg='beekeepercfg.json'):
        self.work_dir = work_dir
        self.config_file = config_arg
        self.config = self.get_config(self.config_file)

        self.servers = {}
        self.greenlets = []
        self.started = False

        database.setup_db(os.path.join(self.config['sql']['connection_string']))
        self.app = app.app
        self.app.config['CERT_PATH'] = self.config['ssl']['certpath']
        self.app.config['BEEKEEPER_CONFIG'] = self.config_file
        self.authenticator = Authenticator()
        self.authenticator.ensure_default_user()

    def start(self, port=5000):
        #management interface
        self.started = True
        logger.info('Starting Beekeeper listening on port {0}'.format(port))

        http_server = WSGIServer(('', 5000), self.app, keyfile='beekeeper.key', certfile='beekeeper.crt')
        http_server_greenlet = gevent.spawn(http_server.serve_forever)
        self.servers['http'] = http_server
        self.greenlets.append(http_server_greenlet)

        maintenance_greenlet = gevent.spawn(self.start_maintenance_tasks)
        self.servers['maintenance'] = maintenance_greenlet
        self.greenlets.append(maintenance_greenlet)

        drop_privileges()
        gevent.joinall(self.greenlets)

    def stop(self):
        self.started = False
        logging.info('Stopping beekeeper.')
        self.servers['http'].stop(5)

    def get_config(self, configfile):
        with open(configfile) as config_file:
            config = json.load(config_file)
        return config

    def start_maintenance_tasks(self):
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




