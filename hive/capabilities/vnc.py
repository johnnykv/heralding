# Copyright (C) 2013 Aniket Panse <contact@aniketpanse.in>
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

import SocketServer
import random

from handlerbase import HandlerBase


def get_random_challenge():
    challenge = []
    for i in range(0, 16):
        temp = random.randint(0, 255)
        challenge.append(chr(temp))
    return "".join(challenge)


class BeeVNCHandler(SocketServer.StreamRequestHandler):

    """
        Handler of VNC Connections. This is a rather primitive state machine.
    """

    RFB_VERSION = "RFB 003.007\n"

    def __init__(self, request, client_address, server, session):
        self.session = session
        SocketServer.StreamRequestHandler.__init__(self, request, client_address, server)

    def handle(self):
        self.request.send(self.RFB_VERSION)
        client_version = self.request.recv(1024)
        if client_version == self.RFB_VERSION:
            self.security_handshake()
        else:
            self.finish()

    def security_handshake(self):
        self.request.send('\x01\x02')
        sec_method = self.request.recv(1024)
        if sec_method == "\x02":
            self.do_vnc_authentication()
        else:
            self.finish()

    def do_vnc_authentication(self):
        challenge = get_random_challenge()
        self.request.send(challenge)
        des_challenge = self.request.recv(1024)

        # This could result in an ugly log file, since the des_challenge is just an array of 4 bytes
        self.session.try_login("", des_challenge)
        self.terminate()

    def terminate(self):
        # Sends authentication failed to the client
        self.request.send("\x00\x00\x00\x01")
        self.finish()


class vnc(HandlerBase):
    def __init__(self, sessions, options):
        super(vnc, self).__init__(sessions, options)
        self._options = options

    def handle_session(self, gsocket, address):
        session = self.create_session(address, gsocket)
        handler = BeeVNCHandler(gsocket, address, None, session)
