# pylint: disable-msg=E1101
# Copyright (C) 2017 Johnny Vestergaard <jkv@unixcluster.dk>
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
from heralding.libs.telnetsrv.telnetsrvlib import TelnetHandlerBase

logger = logging.getLogger(__name__)


class Telnet(HandlerBase):
    def __init__(self, options, loop):
        super().__init__(options, loop)
        TelnetWrapper.max_tries = int(self.options['protocol_specific_data']['max_attempts'])

    async def execute_capability(self, reader, writer, session):
        telnet_cap = TelnetWrapper(reader, writer, session, self.loop)
        await telnet_cap.run()


class TelnetWrapper(TelnetHandlerBase):
    """
    Wraps the telnetsrv module to fit the Honeypot architecture.
    """
    PROMPT = b'$ '
    max_tries = 3
    TERM = 'ansi'

    authNeedUser = True
    authNeedPass = True

    def __init__(self, reader, writer, session, loop):
        self.auth_count = 0
        self.username = None
        self.session = session
        address = writer.get_extra_info('address')
        super().__init__(reader, writer, address, loop)

    async def authentication_ok(self):
        while self.auth_count < TelnetWrapper.max_tries:
            username = await self.readline(prompt=b"Username: ", use_history=False)
            password = await self.readline(echo=False, prompt=b"Password: ", use_history=False)
            self.session.add_auth_attempt(_type='plaintext', username=str(username, 'utf-8'),
                                          password=str(password, 'utf-8'))
            if self.DOECHO:
                self.write(b"\n")
            self.auth_count += 1
        self.writeline(b'Username: ')  # It fixes a problem with Hydra bruteforcer.
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
