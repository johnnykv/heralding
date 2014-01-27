# Copyright (C) 2013 Aniket Panse <contact@aniketpanse.in>
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
gevent.monkey.patch_all()
from gevent.server import StreamServer

import unittest
import os
import shutil
import tempfile

from beeswarm.honeypot.honeypot import Honeypot
from beeswarm.client.models.session import BeeSession
from beeswarm.honeypot.models.authenticator import Authenticator
from beeswarm.honeypot.models.session import Session
from beeswarm.honeypot.models.user import BaitUser
from beeswarm.honeypot.capabilities import https as hive_https
from beeswarm.client.capabilities import https as bee_https


class HTTPS_Test(unittest.TestCase):
    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        Honeypot.prepare_environment(self.work_dir)

    def tearDown(self):
        if os.path.isdir(self.work_dir):
            shutil.rmtree(self.work_dir)

    def test_login(self):
        """ Tests if HTTPs bee can login to the http capability.
        """
        sessions = {}
        users = {'test': BaitUser('test', 'test')}
        authenticator = Authenticator(users)
        Session.authenticator = authenticator
        options = {'enabled': 'True', 'port': 0}
        cap = hive_https.https(sessions, options, users, self.work_dir)
        srv = StreamServer(('0.0.0.0', 0), cap.handle_session)
        srv.start()

        bee_info = {
            'timing': 'regular',
            'username': 'test',
            'password': 'test',
            'port': srv.server_port,
            'server': '127.0.0.1'
        }
        beesessions = {}
        BeeSession.client_id = 'f51171df-c8f6-4af4-86c0-f4e163cf69e8'

        current_bee = bee_https.https(beesessions, bee_info)
        current_bee.do_session('127.0.0.1')
        srv.stop()

if __name__ == '__main__':
    unittest.main()
