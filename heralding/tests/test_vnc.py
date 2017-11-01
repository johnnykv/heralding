# Copyright (C) 2017 Roman Samoilenko <ttahabatt@gmail.com>
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

import os
import asyncio
import unittest

from heralding.capabilities.vnc import Vnc, RFB_VERSION, VNC_AUTH
from heralding.reporting.reporting_relay import ReportingRelay


class VncTests(unittest.TestCase):
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

        self.loop.close()

    def test_vnc_authentication(self):
        async def vnc_auth():
            reader, writer = await asyncio.open_connection('127.0.0.1', 8888,
                                                           loop=self.loop)
            # server rfb version
            _ = await reader.readline()
            writer.write(RFB_VERSION)

            # available auth methods
            _ = await reader.read(1024)
            writer.write(VNC_AUTH)

            # challenge
            _ = await reader.read(1024)
            # Pretending, that we encrypt received challenge with DES and send back the result.
            client_response = os.urandom(16)
            writer.write(client_response)

            # security result
            _ = await reader.read(1024)

        options = {'enabled': 'True', 'port': 8888, 'timeout': 30}
        capability = Vnc(options, self.loop)

        server_coro = asyncio.start_server(capability.handle_session, '0.0.0.0', 8888, loop=self.loop)
        self.server = self.loop.run_until_complete(server_coro)

        self.loop.run_until_complete(vnc_auth())
