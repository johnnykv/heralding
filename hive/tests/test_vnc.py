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
import socket
import unittest
gevent.monkey.patch_all()


from gevent.server import StreamServer
from hive.helpers.common import create_socket
from hive.capabilities import vnc
from hive.models.user import HiveUser


class VNC_Test(unittest.TestCase):

    def test_connection(self):
        """ Tests if the capability is up, and sending
            HTTP 401 (Unauthorized) headers.
        """
        sessions = {}
        users = {'test': HiveUser('test', 'test')}
        cap = vnc.vnc(sessions, {'enabled': 'True', 'port': 5902}, users)
        s = create_socket(("0.0.0.0", 5902))
        srv = StreamServer(s, cap.handle_session)
        srv.start()
        
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(('127.0.0.1', 5902))

        protocol_version = client_socket.recv(1024)
        self.assertEquals(protocol_version, "RFB 003.007\n")

        client_socket.send("RFB 003.007\n")
        supported_auth_methods = client_socket.recv(1024)
        self.assertEquals(supported_auth_methods, "\x01\x02")

        client_socket.send("\x02")
        challenge = client_socket.recv(1024)

        # Send 16 bytes because server expects them. Don't care what they
        # are
        client_socket.send("\x00"*16)
        auth_status = client_socket.recv(1024)
        self.assertEquals(auth_status, "\x00\x00\x00\x01")
        
if __name__ == '__main__':
    unittest.main()
