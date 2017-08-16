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

from heralding.capabilities.ssh import SSH
from heralding.reporting.reporting_relay import ReportingRelay

import asyncssh


class SshTests(unittest.TestCase):
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

    def test_basic_login(self):
        async def run_client():
            async with asyncssh.connect('localhost', port=8888,
                                        username='johnny', password='secretpw',
                                        known_hosts=None, loop=self.loop) as _:
                pass

        ssh_key_file = 'ssh.key'
        SSH.generate_ssh_key(ssh_key_file)

        options = {'enabled': 'True', 'port': 8888}
        server_coro = asyncssh.create_server(lambda: SSH(options, self.loop), '0.0.0.0', 8888,
                                             server_host_keys=['ssh.key'], loop=self.loop)
        self.server = self.loop.run_until_complete(server_coro)

        try:
            self.loop.run_until_complete(run_client())
        except asyncssh.Error:
            pass
