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


import gevent.monkey
gevent.monkey.patch_all()  # NOQA

from gevent.server import StreamServer

from heralding.capabilities import http
from heralding.reporting.reporting_relay import ReportingRelay

import unittest
import httplib


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.reportingRelay = ReportingRelay()
        self.reportingRelay.start()

    def tearDown(self):
        self.reportingRelay.stop()

    def test_connection(self):
        """ Tests if the capability is up, and sending
            HTTP 401 (Unauthorized) headers.
        """

        options = {'enabled': 'True', 'port': 0, 'users': {'test': 'test'}}
        cap = http.Http(options)
        srv = StreamServer(('0.0.0.0', 0), cap.handle_session)
        srv.start()

        client = httplib.HTTPConnection('127.0.0.1', srv.server_port)
        client.request('GET', '/')
        response = client.getresponse()
        self.assertEqual(response.status, 401)
        srv.stop()
