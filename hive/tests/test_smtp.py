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

import gevent.monkey
import smtplib
import base64
import hmac
from hive.helpers.common import create_socket
from gevent.server import StreamServer
from hive.capabilities import smtp
gevent.monkey.patch_all()

import unittest
from hive.models.authenticator import Authenticator
from hive.models.session import Session

authenticator = Authenticator()
Session.authenticator = authenticator


class SMTP_Test(unittest.TestCase):
    
    def test_connection(self):

        sessions = {}
        cap = smtp.smtp(sessions, {'enabled': 'True', 'port': 2525, 'banner': 'Test'})
        socket = create_socket(("0.0.0.0", 2525))
        srv = StreamServer(socket, cap.handle_session)
        srv.start()

        smtp_ = smtplib.SMTP('127.0.0.1', 2525, local_hostname='localhost', timeout=15)
        smtp_.ehlo()
        smtp_.quit()
        
    def test_AUTH_CRAM_MD5(self):
        sessions = {}
        cap = smtp.smtp(sessions, {'enabled': 'True', 'port': 2500, 'banner': 'Test'})
        socket = create_socket(("0.0.0.0", 2500))
        srv = StreamServer(socket, cap.handle_session)
        srv.start()
        
        def encode_cram_md5(challenge, user, password):
            challenge = base64.decodestring(challenge)
            response = user + " " + hmac.HMAC(password, challenge).hexdigest()
            return base64.b64encode(response)

        smtp_ = smtplib.SMTP('127.0.0.1', 2500, local_hostname='localhost', timeout=15)
        _, resp = smtp_.docmd("AUTH", "CRAM-MD5")
        code, resp = smtp_.docmd(encode_cram_md5(resp, "test", "test"))
        # For now, the server's going to return a 535 code.
        self.assertEqual(code, 535)
            
if __name__ == '__main__':
    print "SMSMASMAS"
    unittest.main()
