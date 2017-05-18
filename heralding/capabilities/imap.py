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

import logging
import socket
import base64
import binascii

from heralding.capabilities.handlerbase import HandlerBase

logger = logging.getLogger(__name__)

CRLF = '\r\n'


class Imap(HandlerBase):
    def __init__(self, options):
        super(Imap, self).__init__(options)
        self.max_tries = int(self.options['protocol_specific_data']['max_attempts'])
        self.banner = self.options['protocol_specific_data']['banner']

        self.available_commands = ['authenticate', 'capability', 'login', 'logout', 'noop']
        self.available_mechanisms = ['plain']

    def execute_capability(self, address, socket, session):
        self._handle_session(session, socket)

    def _handle_session(self, session, gsocket):
        fileobj = gsocket.makefile()

        self.send_message(session, gsocket, self.banner)

        state = "Not Authenticated"
        while state != 'Logout' and session.connected:
            try:
                raw_msg = fileobj.readline()
            except socket.error:
                session.end_session()
                break

            cmd_msg = raw_msg.rstrip().split(' ', 2)
            if len(cmd_msg) == 0:
                continue
            elif len(cmd_msg) == 1:
                self.send_message(session, gsocket, "* BAD invalid command")
                continue
            elif len(cmd_msg) == 2:
                tag = cmd_msg[0]
                cmd = cmd_msg[1]
                args = ''
            else:
                tag = cmd_msg[0]
                cmd = cmd_msg[1]
                args = cmd_msg[2]

            cmd = cmd.lower()
            if cmd not in self.available_commands:
                self.send_message(session, gsocket, tag + " BAD invalid command")
            else:
                func_to_call = getattr(self, 'cmd_{0}'.format(cmd), None)
                if func_to_call:
                    return_value = func_to_call(session, gsocket, tag, args)
                    state = return_value
                else:
                    self.send_message(session, gsocket, tag + " BAD invalid command")
        session.end_session()

    def cmd_authenticate(self, session, gsocket, tag, args):
        mechanism = args.split()
        if len(mechanism) == 1:
            auth_mechanism = mechanism[0].lower()
        else:
            self.send_message(session, gsocket, tag + ' BAD invalid command')
            return "Not Authenticated"

        if auth_mechanism in self.available_mechanisms:
            # the space after '+' is needed according to RFC
            self.send_message(session, gsocket, '+ ')
            raw_msg = gsocket.recv(512)

            if auth_mechanism == 'plain':
                success, credentials = self.try_b64decode(raw_msg, session)
                # \x00 is a separator between authorization identity,
                # username and password. Authorization identity isn't used in
                # this auth mechanism, so we must have 2 \x00 symbols.(RFC 4616) 
                if success and credentials.count('\x00') == 2:
                    _, user, password = base64.b64decode(raw_msg).split('\x00')
                    session.add_auth_attempt('plaintext', username=user, password=password)
                    self.send_message(session, gsocket, tag + ' NO Authentication failed')
                else:
                    self.send_message(session, gsocket, tag + ' BAD invalid command')
        else:
            self.send_message(session, gsocket, tag + ' BAD invalid command')
        self.stop_if_too_many_attempts(session)
        return 'Not Authenticated'

    def cmd_capability(self, session, gsocket, tag, args):
        self.send_message(session, gsocket, '* CAPABILITY IMAP4rev1 AUTH=PLAIN')
        self.send_message(session, gsocket, tag + ' OK CAPABILITY completed')
        return 'Not Authenticated'

    def cmd_login(self, session, gsocket, tag, args):
        if args:
            user_cred = args.split(' ', 1)
        else:
            self.send_message(session, gsocket, tag + ' BAD invalid command')
            return 'Not Authenticated'

        # Delete first and last quote,
        # because login and password can be sent as quoted strings
        if len(user_cred) == 1:
            user = self.strip_quotes(user_cred[0])
            password = ''
        else:
            user = self.strip_quotes(user_cred[0])
            password = self.strip_quotes(user_cred[1])

        session.add_auth_attempt('plaintext', username=user, password=password)
        self.send_message(session, gsocket, tag + ' NO Authentication failed')
        self.stop_if_too_many_attempts(session)
        return 'Not Authenticated'

    def cmd_logout(self, session, gsocket, tag, args):
        self.send_message(session, gsocket, '* BYE IMAP4rev1 Server logging out')
        self.send_message(session, gsocket, tag + ' OK LOGOUT completed')
        return 'Logout'

    def cmd_noop(self, session, gsocket, tag, args):
        self.send_message(session, gsocket, tag + ' OK NOOP completed')
        return 'Not Authenticated'

    def send_message(self, session, gsocket, msg):
        try:
            gsocket.sendall(msg + CRLF)
        except socket.error:
            session.end_session()

    def stop_if_too_many_attempts(self, session):
        if self.max_tries < session.get_number_of_login_attempts():
            session.end_session()

    @staticmethod
    def try_b64decode(b64_str, session):
        try:
            result = base64.b64decode(b64_str)
            return True, result
        except TypeError:
            logger.warning('Error decoding base64: {0} '
                           '({1})'.format(binascii.hexlify(b64_str), session.id))
            return False, ''

    @staticmethod
    def strip_quotes(quoted_str):
        if quoted_str.startswith('\"') and quoted_str.endswith('\"'):
            nonquoted_str = quoted_str[1:-1]
        else:
            nonquoted_str = quoted_str
        return nonquoted_str
