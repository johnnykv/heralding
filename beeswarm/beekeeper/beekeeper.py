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

import logging
import os
import shutil
from ConfigParser import ConfigParser

from gevent.wsgi import WSGIServer
import beeswarm
from beeswarm.beekeeper import database_config

logger = logging.getLogger(__name__)


class Beekeeper(object):
    def __init__(self, work_dir, config_file='beekeeper.cfg'):
        self.config = ConfigParser()
        self.config.read(config_file)

        database_config.setup_db(os.path.join(os.getcwd(), self.config.get('sqlite', 'db_file')))
        from beeswarm.beekeeper.webapp import app

        self.app = app.app

    def start(self, port=5000):
        #management interface
        logger.info('Starting Beekeeper listening on port {0}'.format(port))
        self.http_server = WSGIServer(('', 5000), self.app)
        self.http_server.serve_forever()

    def stop(self):
        self.http_server.stop(5)

    @staticmethod
    def prepare_environment(work_dir):
        package_directory = os.path.dirname(os.path.abspath(beeswarm.__file__))
        #no preparation needed as of yet
        config_file = os.path.join(work_dir, 'beekeeper.cfg.dist')
        if not os.path.isfile(config_file):
            logging.info('Copying configuration file to workdir.')
            shutil.copyfile(os.path.join(package_directory, 'beekeeper/beekeeper.cfg.dist'),
                            os.path.join(work_dir, 'beekeeper.cfg'))

