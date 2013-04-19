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

import ftplib
import unittest


from ftplib import FTP
from gevent.server import StreamServer
from hive.helpers.common import create_socket
from hive.capabilities import ftp
from hive.models.authenticator import Authenticator
from hive.models.session import Session


class ftp_Tests(unittest.TestCase):

    def test_login(self):
        """Testing different login combinations"""

        authenticator = Authenticator()
        Session.authenticator = authenticator
        sessions = {}
        cap = ftp.ftp(sessions, {'enabled': 'True', 'port': 2122, 'banner': 'Test Banner', 'max_attempts': 3})
        socket = create_socket(('0.0.0.0', 2122))
        srv = StreamServer(socket, cap.handle_session)
        srv.start()

        ftp_client = FTP()
        ftp_client.connect('127.0.0.1', 2122, 1)

        #expect perm exception
        try:
            ftp_client.login('james', 'bond')
            response = ftp_client.getresp()
        except ftplib.error_perm:
            pass
        srv.stop()

if __name__ == '__main__':
    unittest.main()
