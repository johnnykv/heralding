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
import curses
import sys

import logging
import socket
from beeswarm.errors import AuthenticationFailed

from beeswarm.honeypot.capabilities.handlerbase import HandlerBase
from beeswarm.honeypot.capabilities.shared.shell import Commands

logger = logging.getLogger(__name__)


class telnet(HandlerBase):
    def __init__(self, sessions, options, users, work_dir):
        super(telnet, self).__init__(sessions, options, users, work_dir)

    def handle_session(self, gsocket, address):
        telnet_wrapper.max_tries = int(self.options['max_attempts'])
        session = self.create_session(address, gsocket)
        try:
            telnet_wrapper(address, None, gsocket, session, self.vfsystem)
        except socket.error as err:
            logger.debug('Unexpected end of telnet session: {0}, errno: {1}. ({2})'.format(err, err.errno, session.id))

        session.connected = False


class telnet_wrapper(Commands):
    """
    Wraps the telnetsrv module to fit the Honeypot architecture.
    """

    def __init__(self, client_address, server, socket, session, vfs):
        self.session = session
        self.auth_count = 0
        request = telnet_wrapper.false_request()
        request._sock = socket

        self.vfs = vfs
        Commands.__init__(self, request, client_address, server, vfs, self.session)

    def authCallback(self, username, password):
        while self.auth_count < telnet_wrapper.max_tries:
            if self.session.try_auth(type='plaintext', username=username, password=password):
                self.working_dir = '/'
                self.username = username
                self.PROMPT = '[{0}@{1} {2}]$ '.format(self.username, self.HOSTNAME, self.working_dir)
                return True
            self.writeline('Invalid username/password')
            self.auth_count += 1
            self.authentication_ok()
        raise AuthenticationFailed()

    def session_end(self):
        self.session.connected = False

    def setterm(self, term):

        # Dummy file for the purpose of tests.
        f = open('/dev/null', 'w')
        curses.setupterm(term, f.fileno())  # This will raise if the termtype is not supported
        self.TERM = term
        self.ESCSEQ = {}
        for k in self.KEYS.keys():
            str_ = curses.tigetstr(curses.has_key._capability_names[k])
            if str_:
                self.ESCSEQ[str_] = k
        self.CODES['DEOL'] = curses.tigetstr('el')
        self.CODES['DEL'] = curses.tigetstr('dch1')
        self.CODES['INS'] = curses.tigetstr('ich1')
        self.CODES['CSRLEFT'] = curses.tigetstr('cub1')
        self.CODES['CSRRIGHT'] = curses.tigetstr('cuf1')

    def writecooked(self, text):
        #TODO: Figure out way to log outgoing without logging "echo"
        #self.session.transcript_outgoing(text)
        Commands.writecooked(self, text)
