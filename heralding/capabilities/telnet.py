# pylint: disable-msg=E1101
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
import logging

from heralding.capabilities.handlerbase import HandlerBase
from heralding.capabilities.shared.shell import Commands

logger = logging.getLogger(__name__)


class Telnet(HandlerBase):
    def __init__(self, options):
        super(Telnet, self).__init__(options)
        TelnetWrapper.max_tries = int(self.options['protocol_specific_data']['max_attempts'])

    def execute_capability(self, address, socket, session):
        TelnetWrapper(address, None, socket, session)


class TelnetWrapper(Commands):
    """
    Wraps the telnetsrv module to fit the Honeypot architecture.
    """
    PROMPT = '$ '

    def __init__(self, client_address, server, _socket, session):
        self.session = session
        self.auth_count = 0
        self.username = None
        request = TelnetWrapper.false_request()
        request._sock = _socket
        Commands.__init__(self, request, client_address, server, self.session)

    def authentication_ok(self):
        while self.auth_count < TelnetWrapper.max_tries:
            username = self.readline(prompt="Username: ", use_history=False)
            password = self.readline(echo=False, prompt="Password: ", use_history=False)
            self.session.add_auth_attempt(_type='plaintext', username=username, password=password)
            if self.DOECHO:
                self.write("\n")
            self.writeline('Invalid username/password\n')
            self.auth_count += 1
        return False

    def setterm(self, term):
        # Dummy file for the purpose of tests.
        with open('/dev/null', 'w') as f:
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

    def session_end(self):
        self.session.end_session()
