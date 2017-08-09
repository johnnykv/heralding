# Copyright (C) 2012 Aniket Panse <contact@aniketpanse.in
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

# Aniket Panse <contact@aniketpanse.in> grants Johnny Vestergaard <jkv@unixcluster.dk>
# a perpetual, worldwide, non-exclusive, no-charge, royalty-free, irrevocable
# copyright license to reproduce, prepare derivative works of, publicly
# display, publicly perform, sublicense, relicense, and distribute [the] Contributions
# and such derivative works.

import asyncio
import unittest

from heralding.capabilities import http
from heralding.reporting.reporting_relay import ReportingRelay

import http.client as httpclient


class HttpTests(unittest.TestCase):
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

    def test_connection(self):
        """ Tests if the capability is up, and sending
            HTTP 401 (Unauthorized) headers.
        """
        def http_request():
            client = httpclient.HTTPConnection('127.0.0.1', 8888)
            client.request('GET', '/')
            response = client.getresponse()
            self.assertEqual(response.status, 401)

        options = {'enabled': 'True', 'port': 8888, 'users': {'test': 'test'}}
        http_cap = http.Http(options, self.loop)

        server_coro = asyncio.start_server(http_cap.handle_session, '0.0.0.0', 8888, loop=self.loop)
        self.server = self.loop.run_until_complete(server_coro)

        http_task = self.loop.run_in_executor(None, http_request)
        self.loop.run_until_complete(http_task)
