# Copyright (C) 2013 Johnny Vestergaard <jkv@unixcluster.dk>
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

import logging

from hive.models.session import Session
from telnetsrv.green import TelnetHandler, command

from handlerbase import HandlerBase

logger = logging.getLogger(__name__)


class telnet(HandlerBase, TelnetHandler):
    max_tries = 3

    authNeedUser = True
    authNeedPass = True

    #black voodoo to facilitate parents with different __init__ params
    def __init__(self, *args, **kwargs):
        if len(args) == 2:
            #this is the constructor call for HandlerBase
            sessions = args[0]
            telnet.sessions = sessions
            telnet.port = args[1]
            super(telnet, self).__init__(sessions, telnet.port)
        elif len(args) == 3:
            request = args[0]
            client_address = args[1]
            server = args[2]
            #this session is unique for each connection
            self.session = self.create_session(client_address, args[3])
            self.auth_count = 0
            TelnetHandler.__init__(self, request, client_address, server)

    def authCallback(self, username, password):

        while self.auth_count < telnet.max_tries:
            self.session.try_login(username, password)
            self.writeline('Invalid username/password')
            self.auth_count += 1
            self.authentication_ok()
        raise

    def session_end(self):
        self.session.connected = False

    def handle_session(self, gsocket, address):
        telnet.streamserver_handle(gsocket, address)

    @classmethod
    def streamserver_handle(cls, socket, address):
        '''Translate this class for use in a StreamServer'''
        request = cls.false_request()
        request._sock = socket
        server = None
        cls.logging.debug("Accepted connection, starting telnet session.")
        cls(request, address, server, socket)