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
import tempfile
import shutil

from gevent.wsgi import WSGIServer
import beeswarm
from beeswarm.beekeeper import database_config

database_config.setup_db(os.path.join(os.getcwd(), 'beekeeper_sqlite.db'))

from beeswarm.beekeeper.webapp import app

logger = logging.getLogger(__name__)


class Beekeeper(object):
    def __init__(self, work_dir, config_file='beekeeper.cfg'):
        pass

    def start(self):
        #management interface
        self.http_server = WSGIServer(('', 5000), app.app)
        self.http_server.serve_forever()

    def stop(self):
        self.http_server.stop(5)

    @staticmethod
    def prepare_environment(work_dir):
        package_directory = os.path.dirname(os.path.abspath(beeswarm.__file__))
        #no preparation needed as of yet

