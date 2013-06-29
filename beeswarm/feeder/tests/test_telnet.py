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
import shutil
import tempfile

from gevent.server import StreamServer
from beeswarm.hive.hive import Hive
from beeswarm.hive.models.authenticator import Authenticator
from beeswarm.hive.models.session import Session
from beeswarm.hive.capabilities import telnet as hive_telnet
from beeswarm.hive.models.user import HiveUser
from beeswarm.hive.helpers.common import create_socket

from beeswarm.feeder.bees import telnet as bee_telnet
from beeswarm.feeder.models.session import BeeSession


class Telnet_Test(unittest.TestCase):
    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        Hive.prepare_environment(self.work_dir)

    def tearDown(self):
        if os.path.isdir(self.work_dir):
            shutil.rmtree(self.work_dir)

    def test_login(self):
        """Tests if the Telnet bee can Login to the Telnet capability"""

        sessions = {}
        users = {'test': HiveUser('test', 'test')}
        authenticator = Authenticator(users)
        Session.authenticator = authenticator

        cap = hive_telnet.telnet(sessions, {'enabled': 'True', 'port': 0, 'max_attempts': 3}, users, self.work_dir)
        socket = create_socket(('0.0.0.0', 0))
        srv = StreamServer(socket, cap.handle_session)
        srv.start()

        bee_info = {
            'timing': 'regular',
            'login': 'test',
            'password': 'test',
            'port': srv.server_port,
            'server': '127.0.0.1'
        }
        beesessions = {}

        BeeSession.feeder_id = 'f51171df-c8f6-4af4-86c0-f4e163cf69e8'
        current_bee = bee_telnet.telnet(beesessions, bee_info)
        current_bee.do_session(bee_info['login'], bee_info['password'], bee_info['server'],
                               bee_info['port'], '127.0.0.1')
        session_id, session = beesessions.popitem()

        # Make sure we only spawned one session.
        self.assertEquals(beesessions, {})

        # Make sure we were able to log in.
        self.assertEquals(session.did_login, True)

        srv.stop()

if __name__ == '__main__':
    unittest.main()
