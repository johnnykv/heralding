# -*- coding: utf-8 -*-
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

import os
import unittest

from heralding.reporting.file_logger import FileLogger


class EncodingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        log_filename = "test_csv.log"
        cls.flogger_greenlet = FileLogger(log_filename)

    def test_ascii(self):
        test_login = test_password = "girls_like_python".encode('ascii')
        test_data = {'username': test_login, 'password': test_password}
        self.flogger_greenlet.handle_log_data(test_data)

    def test_unicode(self):
        # word 'python' in russian spelling
        test_login = test_password = u"пайтон"
        test_data = {'username': test_login, 'password': test_password}
        self.flogger_greenlet.handle_log_data(test_data)

    def test_already_in_utf(self):
        test_login = test_password = "пайтон"
        test_data = {'username': test_login, 'password': test_password}
        self.flogger_greenlet.handle_log_data(test_data)

    def test_invalid_utf(self):
        test_login = test_password = "пайт\x80он"
        test_data = {'username': test_login, 'password': test_password}
        self.flogger_greenlet.handle_log_data(test_data)

    @classmethod
    def tearDownClass(cls):
        cls.flogger_greenlet.fileHandler.close()
        os.remove("test_csv.log")
