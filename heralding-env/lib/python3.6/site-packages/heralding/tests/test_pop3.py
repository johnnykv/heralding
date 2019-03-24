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

from heralding.capabilities.pop3 import Pop3
from heralding.misc.common import cancel_all_pending_tasks
from heralding.reporting.reporting_relay import ReportingRelay


class Pop3Tests(unittest.TestCase):
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

    def test_login(self):
        """Testing different login combinations"""
        async def pop3_login():
            login_sequences = [
                # invalid login, invalid password
                (('USER wakkwakk', b'+OK User accepted'), ('PASS wakkwakk', b'-ERR Authentication failed.')),
                # PASS without user
                (('PASS bond', b'-ERR No username given.'),),
                # Try to run a TRANSACITON state command in AUTHORIZATION state
                (('RETR', b'-ERR Unknown command'),),
            ]
            for sequence in login_sequences:
                reader, writer = await asyncio.open_connection('127.0.0.1', 8888,
                                                               loop=self.loop)
                # skip banner
                await reader.readline()

                for pair in sequence:
                    writer.write(bytes(pair[0] + "\r\n", 'utf-8'))
                    response = await reader.readline()
                    self.assertEqual(response.rstrip(), pair[1])

        options = {'port': 110, 'protocol_specific_data': {'max_attempts': 3}, 'users': {'james': 'bond'}}
        sut = Pop3(options, self.loop)

        server_coro = asyncio.start_server(sut.handle_session, '0.0.0.0', 8888, loop=self.loop)
        self.server = self.loop.run_until_complete(server_coro)

        self.loop.run_until_complete(pop3_login())
