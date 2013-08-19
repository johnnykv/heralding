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
from beeswarm.hive.capabilities import ftp as hive_ftp
from beeswarm.hive.models.user import HiveUser
from beeswarm.hive.helpers.common import create_socket

from beeswarm.feeder.bees import ftp as bee_ftp
from beeswarm.feeder.models.session import BeeSession


class FTP_Test(unittest.TestCase):
    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        Hive.prepare_environment(self.work_dir)
        self.create_file_system()

    def tearDown(self):
        if os.path.isdir(self.work_dir):
            shutil.rmtree(self.work_dir)

    def create_file_system(self):
        ftp_dir = os.path.join(self.work_dir, 'data/vfs/pub/ftp')
        f1_path = os.path.join(ftp_dir, 'file_one.txt')
        with open(f1_path, 'w') as f1:
            f1.write('contents of file one!')

        d1_path = os.path.join(ftp_dir, 'dir_one')
        os.mkdir(d1_path)

        f2_path = os.path.join(d1_path, 'file_two.txt')
        with open(f2_path, 'w') as f2:
            f2.write('contents of file two!')

    def test_login(self):
        """FTP: Testing different login combinations"""

        sessions = {}
        users = {'test': HiveUser('test', 'test')}
        authenticator = Authenticator(users)
        Session.authenticator = authenticator

        options = {'enabled': 'True', 'port': 0, 'banner': 'Test Banner', 'max_attempts': 3, 'syst_type': 'Test Type'}

        cap = hive_ftp.ftp(sessions, options, users, self.work_dir)
        socket = create_socket(('0.0.0.0', 0))
        srv = StreamServer(socket, cap.handle_session)
        srv.start()

        bee_info = {
            'enabled': True,
            'timing': 'regular',
            'username': 'test',
            'password': 'test',
            'port': srv.server_port,
            'server': '127.0.0.1'
        }
        beesessions = {}

        BeeSession.feeder_id = 'f51171df-c8f6-4af4-86c0-f4e163cf69e8'
        current_bee = bee_ftp.ftp(beesessions, bee_info)

        current_bee.connect()
        current_bee.login(bee_info['username'], bee_info['password'])
        srv.stop()

    def test_list(self):
        """Tests the FTP LIST command"""

        sessions = {}
        users = {'test': HiveUser('test', 'test')}
        authenticator = Authenticator(users)
        Session.authenticator = authenticator

        options = {'enabled': 'True', 'port': 0, 'banner': 'Test Banner', 'max_attempts': 3, 'syst_type': 'Test Type'}

        cap = hive_ftp.ftp(sessions, options, users, self.work_dir)
        socket = create_socket(('0.0.0.0', 0))
        srv = StreamServer(socket, cap.handle_session)
        srv.start()

        bee_info = {
            'enabled': True,
            'timing': 'regular',
            'username': 'test',
            'password': 'test',
            'port': srv.server_port,
            'server': '127.0.0.1'
        }
        beesessions = {}

        BeeSession.feeder_id = 'f51171df-c8f6-4af4-86c0-f4e163cf69e8'
        current_bee = bee_ftp.ftp(beesessions, bee_info)

        current_bee.connect()
        current_bee.login(bee_info['username'], bee_info['password'])

        current_bee.list()
        self.assertGreater(len(current_bee.state['file_list']), 0)
        self.assertGreater(len(current_bee.state['dir_list']), 0)

        srv.stop()

    def test_cwd(self):
        """Tests the FTP CWD command"""

        sessions = {}
        users = {'test': HiveUser('test', 'test')}
        authenticator = Authenticator(users)
        Session.authenticator = authenticator

        options = {'enabled': 'True', 'port': 0, 'banner': 'Test Banner', 'max_attempts': 3, 'syst_type': 'Test Type'}

        cap = hive_ftp.ftp(sessions, options, users, self.work_dir)
        socket = create_socket(('0.0.0.0', 0))
        srv = StreamServer(socket, cap.handle_session)
        srv.start()

        bee_info = {
            'enabled': True,
            'timing': 'regular',
            'username': 'test',
            'password': 'test',
            'port': srv.server_port,
            'server': '127.0.0.1'
        }
        beesessions = {}

        BeeSession.feeder_id = 'f51171df-c8f6-4af4-86c0-f4e163cf69e8'
        current_bee = bee_ftp.ftp(beesessions, bee_info)

        current_bee.connect()
        current_bee.login(bee_info['username'], bee_info['password'])

        self.assertEquals('/', current_bee.state['current_dir'])
        current_bee.list()
        current_bee.cwd(current_bee.state['dir_list'][0])
        self.assertNotEquals('/', current_bee.state['current_dir'])

        srv.stop()

    def test_retr(self):
        """Tests the FTP RETR command"""

        sessions = {}
        users = {'test': HiveUser('test', 'test')}
        authenticator = Authenticator(users)
        Session.authenticator = authenticator

        options = {'enabled': 'True', 'port': 0, 'banner': 'Test Banner', 'max_attempts': 3, 'syst_type': 'Test Type'}

        cap = hive_ftp.ftp(sessions, options, users, self.work_dir)
        socket = create_socket(('0.0.0.0', 0))
        srv = StreamServer(socket, cap.handle_session)
        srv.start()

        bee_info = {
            'enabled': True,
            'timing': 'regular',
            'username': 'test',
            'password': 'test',
            'port': srv.server_port,
            'server': '127.0.0.1'
        }
        beesessions = {}

        BeeSession.feeder_id = 'f51171df-c8f6-4af4-86c0-f4e163cf69e8'
        current_bee = bee_ftp.ftp(beesessions, bee_info)

        current_bee.connect()
        current_bee.login(bee_info['username'], bee_info['password'])

        current_bee.list()
        current_bee.retrieve(current_bee.state['file_list'][0])

        srv.stop()

if __name__ == '__main__':
    unittest.main()