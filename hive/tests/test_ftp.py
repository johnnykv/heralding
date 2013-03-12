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
from ftplib import FTP
from gevent.server import StreamServer
import unittest
from hive.capabilities import ftp
from hive.models.session import Session
from hive.models.authenticator import Authenticator


class ftp_Tests(unittest.TestCase):
    def test_initial_session(self):
        """Tests if the basic parts of the session is filled correctly"""

        sessions = {}

        #provide valid login/pass to authenticator
        authenticator = Authenticator({'james': 'bond'})
        Session.authenticator = authenticator

        #sut = pop3.pop3(sessions, 110)
        sut = ftp.ftp(sessions, {'port': 21, 'max_attempts': 3, 'banner':'Test Banner', 'enabled':'True'})

        #dont really care about the socket at this point (None...)
        #TODO: mock the socket!
        try:
            sut.handle_session(None, ['192.168.1.200', 12000])
        except AttributeError:
            #because socket is not set
            pass

        #expect a single entry in the sessions dict
        self.assertEqual(1, len(sessions))
        session = sessions.values()[0]
        self.assertEqual(21, session.honey_port)
        self.assertEqual('ftp', session.protocol)
        self.assertEquals('192.168.1.200', session.attacker_ip)
        self.assertEqual(12000, session.attacker_source_port)

    def test_login(self):
        """Testing different login combinations"""

        #provide valid login/pass to authenticator
        #current implementation does allow actual logon.
        authenticator = Authenticator({})
        Session.authenticator = authenticator

        sessions = {}
        sut = ftp.ftp(sessions, {'port': 21, 'max_attempts': 3, 'banner':'Test Banner', 'enabled':'True'})

        server = StreamServer(('127.0.0.1', 0), sut.handle_session)
        server.start()

        ftp_client = FTP()
        ftp_client.connect('127.0.0.1', server.server_port, 1)

        #expect perm exception
        try:
            ftp_client.login('james', 'bond')
            response = ftp_client.getresp()
        except ftplib.error_perm:
            pass

        server.stop()


if __name__ == '__main__':
    unittest.main()
