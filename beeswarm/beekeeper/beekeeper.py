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

logger = logging.getLogger(__name__)


class Beekeeper(object):
    def __init__(self, work_dir, config_arg='beekeepercfg.json'):
        with open(config_arg) as config_file:
            self.config = json.load(config_file)

        self.servers = {}
        self.greenlets = []

        database.setup_db(os.path.join(self.config['sql']['connection_string']))
        self.app = app.app
        self.app.config['CERT_PATH'] = self.config['ssl']['certpath']
        self.authenticator = Authenticator()
        self.authenticator.ensure_default_user()

    def start(self, port=5000):
        #management interface
        logger.info('Starting Beekeeper listening on port {0}'.format(port))

        http_server = WSGIServer(('', 5000), self.app, keyfile='beekeeper.key', certfile='beekeeper.crt')
        http_server_greenlet = gevent.spawn(http_server.serve_forever)
        self.servers['http'] = http_server
        self.greenlets.append(http_server_greenlet)

        #Out of band import because of premature db implementation
        from beeswarm.beekeeper.classifier.classifier import Classifier

        classifier = Classifier()
        classifier_greenlet = gevent.spawn(classifier.start)
        self.servers['classifier'] = classifier
        self.greenlets.append(classifier_greenlet)

        drop_privileges()
        gevent.joinall(self.greenlets)

    def stop(self):
        logging.info('Stopping beekeeper.')
        self.servers['classifier'].stop()
        self.servers['http'].stop(5)
