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
from beeswarm.hive.models.user import HiveUser
from beeswarm.hive.capabilities import telnet

gevent.monkey.patch_all()
from gevent.server import StreamServer

import unittest
import telnetlib
import tempfile
import sys
import os
import shutil

from beeswarm.hive.hive import Hive
from beeswarm.hive.models.session import Session
from beeswarm.hive.models.authenticator import Authenticator


class Telnet_Tests(unittest.TestCase):
    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        Hive.prepare_environment(self.work_dir)

    def tearDown(self):
        if os.path.isdir(self.work_dir):
            shutil.rmtree(self.work_dir)

    def test_invalid_login(self):
        """Tests if telnet server responds correctly to a invalid login attempt."""

        #curses dependency in the telnetserver need a STDOUT with file descriptor.
        sys.stdout = tempfile.TemporaryFile()

        #initialize capability and start tcp server
        authenticator = Authenticator({})
        Session.authenticator = authenticator
        sessions = {}
        users = {'test': HiveUser('test', 'test')}
        sut = telnet.telnet(sessions, {'port': 23, 'max_attempts': 3}, users, self.work_dir)
        server = StreamServer(('127.0.0.1', 0), sut.handle_session)
        server.start()

        client = telnetlib.Telnet('localhost', port=server.server_port)
        #set this to 1 if having problems with this test
        client.set_debuglevel(0)

        #this disables all command negotiation.
        client.set_option_negotiation_callback(self.cb)

        #Expect username as first output
        reply = client.read_until('Username: ', 1)
        self.assertEquals('Username: ', reply)

        client.write('someuser' + '\n')
        reply = client.read_until('Password: ', 5)
        self.assertTrue(reply.endswith('Password: '))

        client.write('somepass' + "\n")
        reply = client.read_until('Invalid username/password\r\nUsername: ')
        self.assertTrue(reply.endswith('Invalid username/password\r\nUsername: '))

        server.stop()

    def cb(self, socket, command, option):
        return

if __name__ == '__main__':
    unittest.main()