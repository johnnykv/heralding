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

from gevent.wsgi import WSGIServer

import database_config
database_config.setup_db(os.path.join(os.getcwd(), 'beekeeper_sqlite.db'))

from webapp import app

logger = logging.getLogger(__name__)


class Beekeeper(object):
    def __init__(self, config_file='beekeeper.cfg'):
        pass

    def start_serving(self):
        #management interface
        self.http_server = WSGIServer(('', 5000), app.app)
        self.http_server.serve_forever()

    def stop_serving(self):
        self.http_server.stop(5)

