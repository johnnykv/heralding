# Copyright (C) 2015 Johnny Vestergaard <jkv@unixcluster.dk>
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

import unittest
import tempfile
import shutil
import os

import gevent
from gevent import Greenlet

from beeswarm.server.server import Server


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.greenlet_exception = None
        self.greenlet_name = None
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.isdir(self.tmpdir):
            shutil.rmtree(self.tmpdir)

    def test_server_startup(self):
        # basic test that checks if we can start and stop the server without errors

        server = Server(self.tmpdir, None, clear_db=True, server_hostname='127.0.0.1', customize=False,
                        reset_password=False, max_sessions=999, start_webui=True)
        server_greenlet = Greenlet.spawn(server.start)
        gevent.sleep(2)
        server.stop()
        gevent.sleep(2)
        server_greenlet.kill()

        # no assert since server will sys.exit(1) on errors



