# -*- coding: utf-8 -*-
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

import sys
import imaplib
import asyncio
import unittest

from heralding.capabilities.imap import Imap
from heralding.reporting.reporting_relay import ReportingRelay


class ImapTests(unittest.TestCase):
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

    def test_LOGIN(self):
        """Testing different login combinations using simple login auth mechanism."""

        def imap_login():
            login_sequences = [
                ('kajoj_admin', 'thebestpassword'),
                ('\"kajoj_admin\"', 'the best password')
            ]

            imap_obj = imaplib.IMAP4('127.0.0.1', port=8888)
            for sequence in login_sequences:
                with self.assertRaises(imaplib.IMAP4.error) as error:
                    imap_obj.login(sequence[0], sequence[1])
                imap_exception = error.exception
                self.assertEqual(imap_exception.args[0], b'Authentication failed')
            imap_obj.logout()

        options = {'enabled': 'True', 'port': 143, 'timeout': 30,
                   'protocol_specific_data': {'max_attempts': 3,
                                              'banner': '* OK IMAP4rev1 Server Ready'}}
        capability = Imap(options, self.loop)
        server_coro = asyncio.start_server(capability.handle_session, '0.0.0.0', 8888, loop=self.loop)
        self.server = self.loop.run_until_complete(server_coro)

        imap_task = self.loop.run_in_executor(None, imap_login)
        self.loop.run_until_complete(imap_task)

    def test_AUTHENTICATE_PLAIN(self):
        """Testing different login combinations using plain auth mechanism."""

        def imap_authenticate():
            # imaplib in Python 3.5.3 and higher returns str representation of auth failure
            # But imaplib in Python 3.5.2 and lower returns bytes.
            # This is a sad hack to get around this problem.
            pyversion = sys.version_info[:3]
            if pyversion < (3, 5, 3):
                auth_failure_msg = b'Authentication failed'
            else:
                auth_failure_msg = 'Authentication failed'
            login_sequences = [
                ('\0kajoj_admin\0thebestpassword', auth_failure_msg),
                ('\0пайтон\0наилучшийпароль', auth_failure_msg),
                ('kajoj_admin\0the best password', 'AUTHENTICATE command error: BAD [b\'invalid command\']')
            ]

            imap_obj = imaplib.IMAP4('127.0.0.1', port=8888)
            for sequence in login_sequences:
                with self.assertRaises(imaplib.IMAP4.error) as error:
                    imap_obj.authenticate('PLAIN', lambda x: sequence[0])
                imap_exception = error.exception
                self.assertEqual(imap_exception.args[0], sequence[1])
            imap_obj.logout()

        options = {'enabled': 'True', 'port': 143, 'timeout': 30,
                   'protocol_specific_data': {'max_attempts': 3,
                                              'banner': '* OK IMAP4rev1 Server Ready'}}
        capability = Imap(options, self.loop)

        server_coro = asyncio.start_server(capability.handle_session, '0.0.0.0', 8888, loop=self.loop)
        self.server = self.loop.run_until_complete(server_coro)

        imap_task = self.loop.run_in_executor(None, imap_authenticate)
        self.loop.run_until_complete(imap_task)


if __name__ == '__main__':
    unittest.main()
