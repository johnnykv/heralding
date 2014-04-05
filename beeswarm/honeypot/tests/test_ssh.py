# Copyright (C) 2012 Johnny Vestergaard <jkv@unixcluster.dk>
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

import gevent
import gevent.monkey
gevent.monkey.patch_all()
from gevent.server import StreamServer

import unittest
import os
import shutil
import tempfile

from beeswarm.honeypot.honeypot import Honeypot
from beeswarm.honeypot.capabilities import ssh
from beeswarm.honeypot.models.session import Session
from beeswarm.honeypot.models.authenticator import Authenticator
from beeswarm.honeypot.models.user import BaitUser
from paramiko import SSHClient, AutoAddPolicy, AuthenticationException


class Telnet_Tests(unittest.TestCase):
    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        Honeypot.prepare_environment(self.work_dir)

        self.key = os.path.join(os.path.dirname( __file__), 'dummy_key.key')
        self.cert = os.path.join(os.path.dirname( __file__), 'dummy_cert.crt')

    def tearDown(self):
        if os.path.isdir(self.work_dir):
            shutil.rmtree(self.work_dir)

    def test_basic_login(self):

        users = {'test': BaitUser('test', 'test')}
        authenticator = Authenticator(users)
        Session.authenticator = authenticator
        sut = ssh.SSH({}, {'port': 0, 'key': self.key}, users, self.work_dir)
        server = StreamServer(('127.0.0.1', 0), sut.handle_session)
        server.start()

        client = SSHClient()
        client.set_missing_host_key_policy(AutoAddPolicy())
        with self.assertRaises(AuthenticationException):
            client.connect('127.0.0.1', server.server_port, 'someuser', 'somepassword')

        server.stop()
