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

from beeswarm.drones.honeypot.honeypot import Honeypot
from beeswarm.drones.honeypot.capabilities import ssh
from paramiko import SSHClient, AutoAddPolicy, AuthenticationException


class SshTests(unittest.TestCase):
    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        self.key = os.path.join(os.path.dirname(__file__), 'dummy_key.key')
        self.cert = os.path.join(os.path.dirname(__file__), 'dummy_cert.crt')
        Honeypot.prepare_environment(self.work_dir)

    def tearDown(self):
        if os.path.isdir(self.work_dir):
            shutil.rmtree(self.work_dir)

    def test_basic_login(self):
        options = {'port': 0, 'users': {'test': 'test'}}
        sut = ssh.SSH({}, options, self.work_dir, self.key)
        server = StreamServer(('127.0.0.1', 0), sut.handle_session)
        server.start()

        client = SSHClient()
        client.set_missing_host_key_policy(AutoAddPolicy())
        with self.assertRaises(AuthenticationException):
            client.connect('127.0.0.1', server.server_port, 'someuser', 'somepassword')

        server.stop()
