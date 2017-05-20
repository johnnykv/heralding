# -*- coding: utf-8 -*-
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

import gevent.monkey

gevent.monkey.patch_all()  # NOQA

from gevent.server import StreamServer

from heralding.capabilities.imap import Imap
from heralding.reporting.reporting_relay import ReportingRelay

import unittest
import imaplib


class ImapTests(unittest.TestCase):
    def setUp(self):
        self.reportingRelay = ReportingRelay()
        self.reportingRelay.start()

    def tearDown(self):
        self.reportingRelay.stop()

    def test_LOGIN(self):
        options = {'enabled': 'True', 'port': 143, 'timeout': 30,
                   'protocol_specific_data': {'max_attempts': 3,
                                              'banner': '* OK IMAP4rev1 Server Ready'}}
        capability = Imap(options)

        server = StreamServer(('0.0.0.0', 2000), capability.handle_session)
        server.start()

        login_sequences = [
            ('kajoj_admin', 'thebestpassword'),
            ('пайтон', 'наилучшийпароль'),  # ('python', 'thebestpassword')
            ('\"kajoj_admin\"', 'the best password')
        ]

        imap_obj = imaplib.IMAP4('127.0.0.1', port=2000)
        for sequence in login_sequences:
            with self.assertRaises(imaplib.IMAP4.error) as error:
                imap_obj.login(sequence[0], sequence[1])
            imap_exception = error.exception
            self.assertEqual(imap_exception.message, 'Authentication failed')

        imap_obj.logout()
        server.stop()

    def test_AUTHENTICATE_PLAIN(self):
        options = {'enabled': 'True', 'port': 143, 'timeout': 30,
                   'protocol_specific_data': {'max_attempts': 3,
                                              'banner': '* OK IMAP4rev1 Server Ready'}}
        capability = Imap(options)

        server = StreamServer(('0.0.0.0', 2000), capability.handle_session)
        server.start()

        login_sequences = [
            ('\0kajoj_admin\0thebestpassword', 'Authentication failed'),
            ('\0пайтон\0наилучшийпароль', 'Authentication failed'),
            ('kajoj_admin\0the best password', 'AUTHENTICATE command error: BAD [\'invalid command\']')
        ]

        imap_obj = imaplib.IMAP4('127.0.0.1', port=2000)
        for sequence in login_sequences:
            with self.assertRaises(imaplib.IMAP4.error) as error:
                imap_obj.authenticate('PLAIN', lambda x: sequence[0])
            imap_exception = error.exception
            self.assertEqual(imap_exception.message, sequence[1])

        imap_obj.logout()
        server.stop()


if __name__ == '__main__':
    unittest.main()
