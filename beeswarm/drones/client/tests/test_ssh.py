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
from beeswarm.drones.honeypot.honeypot import Honeypot
from beeswarm.drones.honeypot.capabilities import ssh as honeypot_ssh

from beeswarm.drones.client.baits import ssh as client_ssh
from beeswarm.drones.client.models.session import BaitSession


class SSH_Test(unittest.TestCase):
    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        Honeypot.prepare_environment(self.work_dir)
        self.key = os.path.join(os.path.dirname(__file__), 'dummy_key.key')
        self.cert = os.path.join(os.path.dirname(__file__), 'dummy_cert.crt')

    def tearDown(self):
        if os.path.isdir(self.work_dir):
            shutil.rmtree(self.work_dir)

    def test_login(self):
        """Tests if the SSH bait can Login to the SSH capability"""

        sessions = {}

        options = {'enabled': 'True', 'port': 0, 'protocol_specific_data': {'max_attempts': 3},
                   'users': {'test': 'test'}}

        cap = honeypot_ssh.SSH(sessions, options, self.work_dir, self.key)

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

        BaitSession.client_id = 'f51171df-c8f6-4af4-86c0-f4e163cf69e8'
        current_bee = client_ssh.ssh(beesessions, bee_info)
        current_bee.connect_login()
        srv.stop()

    def test_logout(self):
        """Tests if the SSH bait can Logout from the SSH capability"""

        sessions = {}
        options = {'enabled': 'True', 'port': 0, 'protocol_specific_data': {'max_attempts': 3},
                   'users': {'test': 'test'}}

        cap = honeypot_ssh.SSH(sessions, options, self.work_dir, self.key)

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

        BaitSession.client_id = 'f51171df-c8f6-4af4-86c0-f4e163cf69e8'
        current_bee = client_ssh.ssh(beesessions, bee_info)
        current_bee.connect_login()
        current_bee.logout()
        srv.stop()

    def test_validate_senses(self):
        sessions = {}

        options = {'enabled': 'True', 'port': 0, 'protocol_specific_data': {'max_attempts': 3},
                   'users': {'test': 'test'}}
        cap = honeypot_ssh.SSH(sessions, options, self.work_dir, self.key)

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

        BaitSession.client_id = 'f51171df-c8f6-4af4-86c0-f4e163cf69e8'
        current_bait = client_ssh.ssh(beesessions, bee_info)
        for s in current_bait.senses:
            sense = getattr(current_bait, s)
            self.assertTrue(callable(sense))

    def test_command_cd(self):

        sessions = {}
        options = {'enabled': 'True', 'port': 0, 'protocol_specific_data': {'max_attempts': 3},
                   'users': {'test': 'test'}}

        cap = honeypot_ssh.SSH(sessions, options, self.work_dir, self.key)

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

        BaitSession.client_id = 'f51171df-c8f6-4af4-86c0-f4e163cf69e8'
        current_bee = client_ssh.ssh(beesessions, bee_info)
        current_bee.connect_login()

        # Command: cd
        self.assertEquals('/', current_bee.state['working_dir'])
        current_bee.cd('/var')
        self.assertEquals('/var', current_bee.state['working_dir'])

    def test_command_pwd(self):

        sessions = {}
        options = {'enabled': 'True', 'port': 0, 'protocol_specific_data': {'max_attempts': 3},
                   'users': {'test': 'test'}}

        cap = honeypot_ssh.SSH(sessions, options, self.work_dir, self.key)

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

        BaitSession.client_id = 'f51171df-c8f6-4af4-86c0-f4e163cf69e8'
        current_bee = client_ssh.ssh(beesessions, bee_info)
        current_bee.connect_login()

        current_bee.cd('/var')
        resp = current_bee.pwd()
        self.assertTrue('/var' in resp)

    def test_command_uname(self):

        sessions = {}
        options = {'enabled': 'True', 'port': 0, 'protocol_specific_data': {'max_attempts': 3},
                   'users': {'test': 'test'}}

        cap = honeypot_ssh.SSH(sessions, options, self.work_dir, self.key)

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

        BaitSession.client_id = 'f51171df-c8f6-4af4-86c0-f4e163cf69e8'
        current_bee = client_ssh.ssh(beesessions, bee_info)
        current_bee.connect_login()

        resp1 = current_bee.uname('-o')
        self.assertTrue('GNU/Linux' in resp1)

    def test_command_cat(self):

        sessions = {}
        options = {'enabled': 'True', 'port': 0, 'protocol_specific_data': {'max_attempts': 3},
                   'users': {'test': 'test'}}

        cap = honeypot_ssh.SSH(sessions, options, self.work_dir, self.key)

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

        BaitSession.client_id = 'f51171df-c8f6-4af4-86c0-f4e163cf69e8'
        current_bee = client_ssh.ssh(beesessions, bee_info)
        current_bee.connect_login()

        # TODO: What is this? html here?
        resp = current_bee.cat('/var/www/index.html')
        self.assertTrue('</html>' in resp)

    def test_command_uptime(self):

        sessions = {}
        options = {'enabled': 'True', 'port': 0, 'protocol_specific_data': {'max_attempts': 3},
                   'users': {'test': 'test'}}

        cap = honeypot_ssh.SSH(sessions, options, self.work_dir, self.key)
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

        BaitSession.client_id = 'f51171df-c8f6-4af4-86c0-f4e163cf69e8'
        current_bee = client_ssh.ssh(beesessions, bee_info)
        current_bee.connect_login()

        resp = current_bee.uptime('-V')
        self.assertTrue('procps version 3.2.8' in resp)

    def test_command_echo(self):

        sessions = {}
        options = {'enabled': 'True', 'port': 0, 'protocol_specific_data': {'max_attempts': 3},
                   'users': {'test': 'test'}}

        cap = honeypot_ssh.SSH(sessions, options, self.work_dir, self.key)

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

        BaitSession.client_id = 'f51171df-c8f6-4af4-86c0-f4e163cf69e8'
        current_bee = client_ssh.ssh(beesessions, bee_info)
        current_bee.connect_login()

        resp = current_bee.echo('just testing!')
        self.assertTrue('just testing!' in resp)

    def test_command_list(self):
        sessions = {}
        options = {'enabled': 'True', 'port': 0, 'protocol_specific_data': {'max_attempts': 3},
                   'users': {'test': 'test'}}
        cap = honeypot_ssh.SSH(sessions, options, self.work_dir, self.key)

        srv = StreamServer(('0.0.0.0', 0), cap.handle_session)
        srv.start()

        bee_info = {
            'timing': 'regular',
            'username': 'test',
            'password': 'test',
            'port': srv.server_port,
            'server': '127.0.0.1',
            'honeypot_id': '1234'
        }
        beesessions = {}

        BaitSession.client_id = 'f51171df-c8f6-4af4-86c0-f4e163cf69e8'
        current_bee = client_ssh.ssh(beesessions, bee_info)
        current_bee.connect_login()

        resp = current_bee.ls()
        self.assertTrue('var' in resp)


if __name__ == '__main__':
    unittest.main()
