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

import ftplib
from ftplib import FTP

from heralding.capabilities import ftp
from heralding.reporting.reporting_relay import ReportingRelay


class FtpTests(unittest.TestCase):
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

    def test_login(self):
        """Testing different login combinations"""

        def ftp_login():
            ftp_client = FTP()
            ftp_client.connect('127.0.0.1', 8888, 1)
            # expect perm exception
            try:
                ftp_client.login('james', 'bond')
                _ = ftp_client.getresp()  # NOQA
            except ftplib.error_perm:
                ftp_client.quit()

        options = {'enabled': 'True', 'port': 0, 'banner': 'Test Banner', 'users': {'test': 'test'},
                   'protocol_specific_data': {'max_attempts': 3, 'banner': 'test banner', 'syst_type': 'Test Type'}}

        ftp_capability = ftp.ftp(options, self.loop)

        server_coro = asyncio.start_server(ftp_capability.handle_session, '0.0.0.0', 8888, loop=self.loop)
        self.server = self.loop.run_until_complete(server_coro)

        ftp_task = self.loop.run_in_executor(None, ftp_login)
        self.loop.run_until_complete(ftp_task)
