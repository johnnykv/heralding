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

import unittest

import gevent
from gevent.server import StreamServer

from heralding.capabilities.pop3 import Pop3
from heralding.reporting.reporting_relay import ReportingRelay


class Pop3Tests(unittest.TestCase):
    def setUp(self):
        self.reportingRelay = ReportingRelay()
        self.reportingRelay.start()

    def tearDown(self):
        self.reportingRelay.stop()

    def test_initial_session(self):
        """Tests if the basic parts of the session is filled correctly"""

        options = {'port': 110, 'protocol_specific_data': {'max_attempts': 3}}
        sut = Pop3(options)

        # dont really care about the socket at this point (None...)
        # TODO: mock the socket!
        try:
            sut.handle_session(None, ['192.168.1.200', 12000])
        except AttributeError:
            # because socket is not set
            pass

            # TODO: Bind to SERVER_RELAY and assert that we get messages as expected
            # self.assertEqual(0, len(sut.sessions))
            # session = sut.sessions.values()[0]
            # self.assertEqual('pop3', session.protocol)
            # self.assertEquals('192.168.1.200', session.source_ip)
            # self.assertEqual(12000, session.source_port)

    def test_login(self):
        """Testing different login combinations"""

        login_sequences = [
            # invalid login, invalid password
            (('USER wakkwakk', '+OK User accepted'), ('PASS wakkwakk', '-ERR Authentication failed.')),
            # PASS without user
            (('PASS bond', '-ERR No username given.'),),
            # Try to run a TRANSACITON state command in AUTHORIZATION state
            (('RETR', '-ERR Unknown command'),),
        ]

        options = {'port': 110, 'protocol_specific_data': {'max_attempts': 3}, 'users': {'james': 'bond'}}
        sut = Pop3(options)

        server = StreamServer(('127.0.0.1', 0), sut.handle_session)
        server.start()

        for sequence in login_sequences:
            client = gevent.socket.create_connection(('127.0.0.1', server.server_port))

            fileobj = client.makefile()

            # skip banner
            fileobj.readline()

            for pair in sequence:
                client.sendall(pair[0] + "\r\n")
                response = fileobj.readline().rstrip()
                self.assertEqual(response, pair[1])

        server.stop()
