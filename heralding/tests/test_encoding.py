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

import unittest

from heralding.reporting.file_logger import get_utf_repr


class EncodingTests(unittest.TestCase):
    def test_ascii(self):
        test_login = "girls_like_python".encode('ascii')
        utf_login = get_utf_repr(test_login)
        expected_utf = "girls_like_python"
        self.assertEqual(utf_login, expected_utf)

    def test_unicode(self):
        # word 'python' in russian spelling
        test_login = u"пайтон"
        utf_login = get_utf_repr(test_login)
        expected_utf = "пайтон"
        self.assertEqual(utf_login, expected_utf)

    def test_already_in_utf(self):
        test_login = "пайтон"
        utf_login = get_utf_repr(test_login)
        expected_utf = "пайтон"
        self.assertEqual(utf_login, expected_utf)

    def test_invalid_utf(self):
        test_login = "пайт\x80он"
        utf_login = get_utf_repr(test_login)
        expected_utf = "пайт?он"
        self.assertEqual(utf_login, expected_utf)
