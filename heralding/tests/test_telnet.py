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

import asyncio
import unittest

import telnetlib

from heralding.capabilities import telnet
from heralding.misc.common import cancel_all_pending_tasks
from heralding.reporting.reporting_relay import ReportingRelay


class TelnetTests(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(None)

        self.reporting_relay = ReportingRelay()
        self.reporting_relay_task = self.loop.run_in_executor(None, self.reporting_relay.start)

    def tearDown(self):
        self.reporting_relay.stop()
        # We give reporting_relay a chance to be finished
        self.loop.run_until_complete(self.reporting_relay_task)

        self.server.close()
        self.loop.run_until_complete(self.server.wait_closed())

        self.loop.run_until_complete(cancel_all_pending_tasks(self.loop))
        self.loop.close()

    def test_invalid_login(self):
        """Tests if telnet server responds correctly to a invalid login attempt."""

        def telnet_login():
            client = telnetlib.Telnet('localhost', 2503)
            # set this to 1 if having problems with this test
            client.set_debuglevel(0)
            # this disables all command negotiation.
            client.set_option_negotiation_callback(self.cb)
            # Expect username as first output

            reply = client.read_until(b'Username: ', 1)
            self.assertEqual(b'Username: ', reply)

            client.write(b'someuser' + b'\r\n')
            reply = client.read_until(b'Password: ', 5)
            self.assertTrue(reply.endswith(b'Password: '))

            client.write(b'somepass' + b'\r\n')
            reply = client.read_until(b'\n', 5)
            self.assertTrue(b'\n' in reply)

            client.close()

        options = {'enabled': 'True', 'port': 2503, 'protocol_specific_data': {'max_attempts': 3},
                   'users': {'test': 'test'}}
        telnet_cap = telnet.Telnet(options, self.loop)

        server_coro = asyncio.start_server(telnet_cap.handle_session, '0.0.0.0', 2503, loop=self.loop)
        self.server = self.loop.run_until_complete(server_coro)

        telnet_task = self.loop.run_in_executor(None, telnet_login)
        self.loop.run_until_complete(telnet_task)

    def cb(self, socket, command, option):
        return
