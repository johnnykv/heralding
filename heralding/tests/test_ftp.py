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
from heralding.tests.common import BaseCapabilityTests
from heralding.reporting.reporting_relay import ReportingRelay


class FtpTests(BaseCapabilityTests):
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
        self.capability_test(ftp.ftp, ftp_login, options)
