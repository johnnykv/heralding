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

import unittest
import os
import tempfile
import shutil

from gevent.server import StreamServer
from beeswarm.drones.honeypot.honeypot import Honeypot
from beeswarm.drones.honeypot.models.user import BaitUser
from beeswarm.drones.honeypot.models.authenticator import Authenticator
from beeswarm.drones.honeypot.models.session import Session
from beeswarm.drones.honeypot.capabilities import pop3s as hive_pop3s

from beeswarm.drones.client.models.session import BeeSession


class POP3S_Test(unittest.TestCase):
    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        Honeypot.prepare_environment(self.work_dir)

    def tearDown(self):
        if os.path.isdir(self.work_dir):
            shutil.rmtree(self.work_dir)

    def test_login(self):
        """Tests if the POP3s bee can login to the POP3 capability"""

        sessions = {}
        users = {'test': BaitUser('test', 'test')}
        authenticator = Authenticator(users)
        Session.authenticator = authenticator

        options = {'enabled': 'True', 'port': 0, 'max_attempts': 3}
        cap = hive_pop3s.Pop3S(sessions, options, users, self.work_dir)
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

        current_bee = bee_pop3s.pop3s(beesessions, bee_info)
        current_bee.do_session('127.0.0.1')
        srv.stop()

if __name__ == '__main__':
    unittest.main()
