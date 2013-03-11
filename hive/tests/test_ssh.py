__author__ = 'jkv'
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
from hive.capabilities import ssh
from hive.models.session import Session
from hive.models.authenticator import Authenticator

from paramiko import SSHClient, AutoAddPolicy, AuthenticationException

class Telnet_Tests(unittest.TestCase):
    def test_basic_login(self):

        authenticator = Authenticator({})
        Session.authenticator = authenticator

        sut = ssh.ssh({}, {'port': 22, 'key': 'hive/tests/dummy_key.key'})
        server = StreamServer(('127.0.0.1', 0), sut.handle_session)
        server.start()
        print server

        client = SSHClient()
        client.set_missing_host_key_policy(AutoAddPolicy())
        with self.assertRaises(AuthenticationException):
            client.connect('127.0.0.1', server.server_port, 'someuser', 'somepassword')

        server.stop()
