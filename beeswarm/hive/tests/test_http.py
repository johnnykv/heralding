# Copyright (C) 2012 Aniket Panse <contact@aniketpanse.in
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

import gevent.monkey
from beeswarm.hive.models.user import HiveUser

gevent.monkey.patch_all()

from gevent.server import StreamServer
from beeswarm.hive.helpers.common import create_socket
from beeswarm.hive.capabilities import http

import unittest
import httplib
import base64
import tempfile
import shutil
import os
from beeswarm.hive.hive import Hive
from beeswarm.hive.models.authenticator import Authenticator
from beeswarm.hive.models.session import Session


class HTTP_Test(unittest.TestCase):
    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        Hive.prepare_environment(self.work_dir)

    def tearDown(self):
        if os.path.isdir(self.work_dir):
            shutil.rmtree(self.work_dir)

    def test_connection(self):
        """ Tests if the capability is up, and sending
            HTTP 401 (Unauthorized) headers.
        """

        sessions = {}
        users = {'test': HiveUser('test', 'test')}
        authenticator = Authenticator(users)
        Session.authenticator = authenticator

        # Use uncommon port so that you can run the test even if the Hive
        # is running.
        options = {'enabled': 'True', 'port': 0}
        cap = http.http(sessions, options, users, self.work_dir)
        socket = create_socket(('0.0.0.0', 0))
        srv = StreamServer(socket, cap.handle_session)
        srv.start()

        client = httplib.HTTPConnection('127.0.0.1', srv.server_port)
        client.request('GET', '/')
        response = client.getresponse()
        self.assertEqual(response.status, 401)
        srv.stop()

    def test_login(self):
        """ Tries to login using the username/password as test/test.
        """
        authenticator = Authenticator({'test': HiveUser('test', 'test')})
        Session.authenticator = authenticator

        sessions = {}
        users = {'test': HiveUser('test', 'test')}
        cap = http.http(sessions, {'enabled': 'True', 'port': 0}, users, self.work_dir)
        socket = create_socket(('0.0.0.0', 0))
        srv = StreamServer(socket, cap.handle_session)
        srv.start()

        client = httplib.HTTPConnection('127.0.0.1', srv.server_port)
        client.putrequest('GET', '/')
        client.putheader('Authorization', 'Basic ' + base64.b64encode('test:test'))
        client.endheaders()
        response = client.getresponse()
        self.assertEqual(response.status, 200)
        srv.stop()

if __name__ == '__main__':
    unittest.main()
