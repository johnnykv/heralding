# Copyright (C) 2018 Roman Samoilenko <ttahabatt@gmail.com>
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

import heralding.capabilities.socks5 as socks
from heralding.reporting.reporting_relay import ReportingRelay


class Socks5Tests(unittest.TestCase):

  def setUp(self):
    self.loop = asyncio.new_event_loop()
    asyncio.set_event_loop(None)

    self.reporting_relay = ReportingRelay()
    self.reporting_relay_task = self.loop.run_in_executor(
        None, self.reporting_relay.start)

  def tearDown(self):
    self.reporting_relay.stop()
    # We give reporting_relay a chance to be finished
    self.loop.run_until_complete(self.reporting_relay_task)

    self.server.close()
    self.loop.run_until_complete(self.server.wait_closed())

    self.loop.close()

  def test_socks_authentication(self):

    async def socks_auth():
      reader, writer = await asyncio.open_connection(
          '127.0.0.1', 8888, loop=self.loop)

      # Greeting to the server. version+authmethod number+authmethod
      client_greeting = socks.SOCKS_VERSION + b"\x01" + socks.AUTH_METHOD
      writer.write(client_greeting)

      # Receive version+chosen authmethod
      _ = await reader.read(2)

      # Send credentials.
      # version+username len+username+password len+password
      credentials = b"\x05\x08username\x08password"
      writer.write(credentials)

      # Receive authmethod+\xff
      res = await reader.read(2)
      self.assertEqual(res, socks.AUTH_METHOD + socks.SOCKS_FAIL)

    options = {'enabled': 'True', 'port': 8888, 'timeout': 30}
    capability = socks.Socks5(options, self.loop)

    server_coro = asyncio.start_server(
        capability.handle_session, '127.0.0.1', 8888, loop=self.loop)
    self.server = self.loop.run_until_complete(server_coro)
    self.loop.run_until_complete(socks_auth())
