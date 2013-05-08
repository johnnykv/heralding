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
from beeswarm.hive.hive import Hive
from beeswarm.hive.helpers.common import create_socket
from beeswarm.hive.models.user import HiveUser
from beeswarm.hive.models.authenticator import Authenticator
from beeswarm.hive.models.session import Session
from beeswarm.hive.capabilities import pop3 as hive_pop3

from beeswarm.feeder.models.session import BeeSession
from beeswarm.feeder.bees import pop3 as bee_pop3


class POP3_Test(unittest.TestCase):
    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        Hive.prepare_environment(self.work_dir)

    def tearDown(self):
        if os.path.isdir(self.work_dir):
            shutil.rmtree(self.work_dir)

    def test_pop3(self):
        """Tests if the POP3 bee can login to the POP3 capability"""

        sessions = {}
        users = {'test': HiveUser('test', 'test')}
        authenticator = Authenticator(users)
        Session.authenticator = authenticator

        cap = hive_pop3.pop3(sessions, {'enabled': 'True', 'port': 8081, 'max_attempts': 3}, users, self.work_dir)
        socket = create_socket(('0.0.0.0', 8081))
        srv = StreamServer(socket, cap.handle_session)
        srv.start()

        bee_info = {
            'timing': 'regular',
            'login': 'test',
            'password': 'test',
            'port': '8080',
            'server': '127.0.0.1'
        }
        beesessions = {}

        BeeSession.feeder_id = 'f51171df-c8f6-4af4-86c0-f4e163cf69e8'

        current_bee = bee_pop3.pop3(beesessions)
        current_bee.do_session(bee_info['login'], bee_info['password'], bee_info['server'],
                               bee_info['port'], '127.0.0.1')
        srv.stop()

if __name__ == '__main__':
    unittest.main()
