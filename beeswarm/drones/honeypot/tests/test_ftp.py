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
import gevent
import gevent.monkey

gevent.monkey.patch_all()

import unittest
import tempfile
import shutil
import os

import ftplib
from ftplib import FTP
from gevent.server import StreamServer
from beeswarm.drones.honeypot.honeypot import Honeypot
from beeswarm.drones.honeypot.capabilities import ftp


class FtpTests(unittest.TestCase):
    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        Honeypot.prepare_environment(self.work_dir)

    def tearDown(self):
        if os.path.isdir(self.work_dir):
            shutil.rmtree(self.work_dir)

    def test_login(self):
        """Testing different login combinations"""

        sessions = {}

        options = {'enabled': 'True', 'port': 0, 'banner': 'Test Banner', 'users': {'test': 'test'},
                   'protocol_specific_data': {'max_attempts': 3, 'banner': 'test banner', 'syst_type': 'Test Type'}}
        cap = ftp.ftp(sessions, options, self.work_dir)
        srv = StreamServer(('0.0.0.0', 0), cap.handle_session)
        srv.start()

        ftp_client = FTP()
        ftp_client.connect('127.0.0.1', srv.server_port, 1)

        # expect perm exception
        try:
            ftp_client.login('james', 'bond')
            response = ftp_client.getresp()
        except ftplib.error_perm:
            pass
        srv.stop()
