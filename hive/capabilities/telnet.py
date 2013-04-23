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
import socket
import errno

from telnetsrv.green import TelnetHandler

from handlerbase import HandlerBase

logger = logging.getLogger(__name__)


class telnet(HandlerBase):
    def __init__(self, sessions, options):
        super(telnet, self).__init__(sessions, options)

    def handle_session(self, gsocket, address):
        telnet_wrapper.max_tries = int(self.options['max_attempts'])
        session = self.create_session(address, gsocket)
        try:
            telnet_wrapper(address, None, gsocket, session)
        except socket.error as err:
            logger.debug('Unexpected end of telnet session: {0}, errno: {1}. ({2})'.format(err, err.errno, session.id))

        session.connected = False


class telnet_wrapper(TelnetHandler):
    """
    Wraps the telnetsrv module to fit the Hive architecture.
    """
    max_tries = 3

    authNeedUser = True
    authNeedPass = True

    def __init__(self, client_address, server, socket, session):
        self.session = session
        self.auth_count = 0
        request = telnet_wrapper.false_request()
        request._sock = socket
        TelnetHandler.__init__(self, request, client_address, server)

    def authCallback(self, username, password):
        while self.auth_count < telnet_wrapper.max_tries:
            self.session.try_auth(type='plaintext', username=username, password=password)
            self.writeline('Invalid username/password')
            self.auth_count += 1
            self.authentication_ok()
        raise

    def session_end(self):
        self.session.connected = False
