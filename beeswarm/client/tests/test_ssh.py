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
from beeswarm.honeypot.honeypot import Honeypot
from beeswarm.honeypot.models.authenticator import Authenticator
from beeswarm.honeypot.models.session import Session
from beeswarm.honeypot.capabilities import ssh as hive_ssh
from beeswarm.honeypot.models.user import BaitUser

from beeswarm.client.capabilities import ssh as bee_ssh
from beeswarm.client.models.session import BeeSession


class SSH_Test(unittest.TestCase):
    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        Honeypot.prepare_environment(self.work_dir)
        self.key = os.path.join(os.path.dirname( __file__), 'dummy_key.key')
        self.cert = os.path.join(os.path.dirname( __file__), 'dummy_cert.crt')

    def tearDown(self):
        if os.path.isdir(self.work_dir):
            shutil.rmtree(self.work_dir)

    def test_login(self):
        """Tests if the SSH bee can Login to the SSH capability"""

        sessions = {}
        users = {'test': BaitUser('test', 'test')}
        authenticator = Authenticator(users)
        Session.authenticator = authenticator

        cap = hive_ssh.SSH(sessions, {'enabled': 'True', 'port': 0, 'max_attempts': 3, 'key': self.key}, users,
                           self.work_dir)
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
        current_bee = bee_ssh.ssh(beesessions, bee_info)
        current_bee.connect_login()
        srv.stop()

    def test_logout(self):
        """Tests if the SSH bee can Logout from the SSH capability"""

        sessions = {}
        users = {'test': BaitUser('test', 'test')}
        authenticator = Authenticator(users)
        Session.authenticator = authenticator

        cap = hive_ssh.SSH(sessions, {'enabled': 'True', 'port': 0, 'max_attempts': 3, 'key': self.key}, users,
                           self.work_dir)
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
        current_bee = bee_ssh.ssh(beesessions, bee_info)
        current_bee.connect_login()
        current_bee.logout()
        srv.stop()

    def test_validate_senses(self):
        sessions = {}
        users = {'test': BaitUser('test', 'test')}
        authenticator = Authenticator(users)
        Session.authenticator = authenticator

        cap = hive_ssh.SSH(sessions, {'enabled': 'True', 'port': 0, 'max_attempts': 3, 'key': self.key}, users,
                           self.work_dir)
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
        current_bee = bee_ssh.ssh(beesessions, bee_info)
        for s in current_bee.senses:
            sense = getattr(current_bee, s)
            self.assertTrue(callable(sense))

    def test_command_cd(self):

        sessions = {}
        users = {'test': BaitUser('test', 'test')}
        authenticator = Authenticator(users)
        Session.authenticator = authenticator

        cap = hive_ssh.SSH(sessions, {'enabled': 'True', 'port': 0, 'max_attempts': 3, 'key': self.key}, users,
                           self.work_dir)
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
        current_bee = bee_ssh.ssh(beesessions, bee_info)
        current_bee.connect_login()

        # Command: cd
        self.assertEquals('/', current_bee.state['working_dir'])
        current_bee.cd('/var')
        self.assertEquals('/var', current_bee.state['working_dir'])

    def test_command_pwd(self):

        sessions = {}
        users = {'test': BaitUser('test', 'test')}
        authenticator = Authenticator(users)
        Session.authenticator = authenticator

        cap = hive_ssh.SSH(sessions, {'enabled': 'True', 'port': 0, 'max_attempts': 3, 'key': self.key}, users,
                           self.work_dir)
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
        current_bee = bee_ssh.ssh(beesessions, bee_info)
        current_bee.connect_login()

        current_bee.cd('/var')
        resp = current_bee.pwd()
        self.assertTrue('/var' in resp)

    def test_command_uname(self):

        sessions = {}
        users = {'test': BaitUser('test', 'test')}
        authenticator = Authenticator(users)
        Session.authenticator = authenticator

        cap = hive_ssh.SSH(sessions, {'enabled': 'True', 'port': 0, 'max_attempts': 3, 'key': self.key}, users,
                           self.work_dir)
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
        current_bee = bee_ssh.ssh(beesessions, bee_info)
        current_bee.connect_login()

        resp1 = current_bee.uname('-o')
        self.assertTrue('GNU/Linux' in resp1)

    def test_command_cat(self):

        sessions = {}
        users = {'test': BaitUser('test', 'test')}
        authenticator = Authenticator(users)
        Session.authenticator = authenticator

        cap = hive_ssh.SSH(sessions, {'enabled': 'True', 'port': 0, 'max_attempts': 3, 'key': self.key}, users,
                           self.work_dir)
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
        current_bee = bee_ssh.ssh(beesessions, bee_info)
        current_bee.connect_login()

        resp = current_bee.cat('/var/www/index.html')
        self.assertTrue('</html>' in resp)

    def test_command_uptime(self):

        sessions = {}
        users = {'test': BaitUser('test', 'test')}
        authenticator = Authenticator(users)
        Session.authenticator = authenticator

        cap = hive_ssh.SSH(sessions, {'enabled': 'True', 'port': 0, 'max_attempts': 3, 'key': self.key}, users,
                           self.work_dir)
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
        current_bee = bee_ssh.ssh(beesessions, bee_info)
        current_bee.connect_login()

        resp = current_bee.uptime('-V')
        self.assertTrue('procps version 3.2.8' in resp)

    def test_command_echo(self):

        sessions = {}
        users = {'test': BaitUser('test', 'test')}
        authenticator = Authenticator(users)
        Session.authenticator = authenticator

        cap = hive_ssh.SSH(sessions, {'enabled': 'True', 'port': 0, 'max_attempts': 3, 'key': self.key}, users,
                           self.work_dir)
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
        current_bee = bee_ssh.ssh(beesessions, bee_info)
        current_bee.connect_login()

        resp = current_bee.echo('just testing!')
        self.assertTrue('just testing!' in resp)

    def test_command_list(self):
        sessions = {}
        users = {'test': BaitUser('test', 'test')}
        authenticator = Authenticator(users)
        Session.authenticator = authenticator

        cap = hive_ssh.SSH(sessions, {'enabled': 'True', 'port': 0, 'max_attempts': 3, 'key': self.key}, users,
                           self.work_dir)
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
        current_bee = bee_ssh.ssh(beesessions, bee_info)
        current_bee.connect_login()

        resp = current_bee.ls()
        self.assertTrue('var' in resp)


if __name__ == '__main__':
    unittest.main()
