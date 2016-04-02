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

import logging
import socket

from heralding.capabilities.handlerbase import HandlerBase

logger = logging.getLogger(__name__)


class Pop3(HandlerBase):
    max_tries = 10
    cmds = {}

    def __init__(self, options, ):
        super(Pop3, self).__init__(options)
        Pop3.max_tries = int(self.options['protocol_specific_data']['max_attempts'])

    def execute_capability(self, address, socket, session):
        self._handle_session(session, socket)

    def _handle_session(self, session, gsocket):
        fileobj = gsocket.makefile()

        self.send_message(session, gsocket, '+OK POP3 server ready')

        state = 'AUTHORIZATION'
        while state != '' and session.connected:
            try:
                raw_msg = fileobj.readline()
            except socket.error:
                session.end_session()
                break

            session.activity()
            cmd_msg = raw_msg.rstrip().split(' ', 1)
            if len(cmd_msg) == 0:
                continue
            elif len(cmd_msg) == 1:
                cmd = cmd_msg[0]
                msg = ''
            else:
                cmd = cmd_msg[0]
                msg = cmd_msg[1]

            cmd = cmd.lower()

            if cmd not in ['apop', 'user', 'pass', 'quit']:
                self.send_message(session, gsocket, '-ERR Unknown command')
            else:
                func_to_call = getattr(self, 'cmd_{0}'.format(cmd), None)
                return_value = func_to_call(session, gsocket, msg)
                # state changers!
                if state == 'AUTHORIZATION' or cmd == 'quit':
                    state = return_value

        session.end_session()

    # APOP mrose c4c9334bac560ecc979e58001b3e22fb
    # +OK mrose's maildrop has 2 messages (320 octets)
    def auth_apop(self, session, gsocket, msg):
        raise Exception('Not implemented yet!')

    # USER mrose
    # +OK User accepted
    # PASS tanstaaf
    # +OK Pass accepted
    # or: "-ERR Authentication failed."
    # or: "-ERR No username given."
    def cmd_user(self, session, gsocket, msg):
        session.vdata['USER'] = msg
        self.send_message(session, gsocket, '+OK User accepted')
        return 'AUTHORIZATION'

    def cmd_pass(self, session, gsocket, msg):
        if 'USER' not in session.vdata:
            self.send_message(session, gsocket, '-ERR No username given.')
        else:
            session.add_auth_attempt('plaintext', username=session.vdata['USER'], password=msg)
            self.send_message(session, gsocket, "-ERR Authentication failed.")

        if 'USER' in session.vdata:
            del session.vdata['USER']
        return 'AUTHORIZATION'

    def cmd_noop(self, session, gsocket, msg):
        self.send_message(session, gsocket, '+OK')

    def cmd_quit(self, session, gsocket, msg):
        self.send_message(session, gsocket, '+OK Logging out')
        return ''

    def not_impl(self, session, gsocket, msg):
        raise Exception('Not implemented yet!')

    def send_message(self, session, gsocket, msg):
        try:
            gsocket.sendall(msg + "\n")
        except socket.error, (value, exceptionMessage):
            session.end_session()

    def send_data(self, session, gsocket, data):
        try:
            gsocket.sendall(data)
        except socket.error, (value, exceptionMessage):
            session.end_session()
