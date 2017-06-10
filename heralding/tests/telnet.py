# Copyright (C) 2017 Johnny Vestergaard <jkv@unixcluster.dk>
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

gevent.monkey.patch_all()  # NOQA
from gevent.server import StreamServer

import unittest
import telnetlib

from heralding.capabilities import telnet
from heralding.reporting.reporting_relay import ReportingRelay


class TelnetTests(unittest.TestCase):
    def setUp(self):
        self.reportingRelay = ReportingRelay()
        self.reportingRelay.start()

    def tearDown(self):
        self.reportingRelay.stop()

    def test_invalid_login(self):
        """Tests if telnet server responds correctly to a invalid login attempt."""

        # initialize capability and start tcp server
        options = {'enabled': 'True', 'port': 2503, 'protocol_specific_data': {'max_attempts': 3},
                   'users': {'test': 'test'}}

        cap = telnet.Telnet(options)
        server = StreamServer(('0.0.0.0', 2503), cap.handle_session)
        server.start()

        client = telnetlib.Telnet('localhost', 2503)
        # set this to 1 if having problems with this test
        client.set_debuglevel(0)

        # this disables all command negotiation.
        client.set_option_negotiation_callback(self.cb)

        # Expect username as first output
        reply = client.read_until(b'Username: ', 1)
        self.assertEquals(b'Username: ', reply)

        client.write(b'someuser' + b'\r\n')
        reply = client.read_until(b'Password: ', 5)
        self.assertTrue(reply.endswith(b'Password: '))

        client.write(b'somepass' + b'\r\n')
        reply = client.read_until(b'Invalid username/password', 5)
        self.assertTrue(b'Invalid username/password' in reply)
        server.stop()

    def cb(self, socket, command, option):
        return
