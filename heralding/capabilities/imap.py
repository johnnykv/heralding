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

import base64
import logging
import binascii

from heralding.capabilities.handlerbase import HandlerBase

logger = logging.getLogger(__name__)

CRLF = '\r\n'


class Imap(HandlerBase):
    def __init__(self, options, loop):
        super().__init__(options, loop)
        self.max_tries = int(self.options['protocol_specific_data']['max_attempts'])
        self.banner = self.options['protocol_specific_data']['banner']

        self.available_commands = ['authenticate', 'capability', 'login', 'logout', 'noop']
        self.available_mechanisms = ['plain']

    async def execute_capability(self, reader, writer, session):
        await self._handle_session(session, reader, writer)

    async def _handle_session(self, session, reader, writer,):
        await self.send_message(writer, self.banner)

        state = "Not Authenticated"
        while state != 'Logout' and session.connected:
            # An exception is raised inside await reader.readline() in case of
            # sudden connection reset.
            raw_msg = await reader.readline()
            if not raw_msg:
                break

            raw_msg_str = str(raw_msg, 'utf-8')

            cmd_msg = raw_msg_str.rstrip().split(' ', 2)
            if len(cmd_msg) == 0:
                continue
            elif len(cmd_msg) == 1:
                await self.send_message(writer, "* BAD invalid command")
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
                await self.send_message(writer, tag + " BAD invalid command")
            else:
                func_to_call = getattr(self, 'cmd_{0}'.format(cmd), None)
                if func_to_call:
                    return_value = await func_to_call(session, reader, writer, tag, args)
                    state = return_value
                else:
                    await self.send_message(writer, tag + " BAD invalid command")
        session.end_session()

    async def cmd_authenticate(self, session, reader, writer, tag, args):
        mechanism = args.split()
        if len(mechanism) == 1:
            auth_mechanism = mechanism[0].lower()
        else:
            await self.send_message(writer, tag + ' BAD invalid command')
            return "Not Authenticated"

        if auth_mechanism in self.available_mechanisms:
            # the space after '+' is needed according to RFC
            await self.send_message(writer, '+ ')
            raw_msg = await reader.read(512)

            if auth_mechanism == 'plain':
                success, credentials = self.try_b64decode(raw_msg, session)
                # \x00 is a separator between authorization identity,
                # username and password. Authorization identity isn't used in
                # this auth mechanism, so we must have 2 \x00 symbols.(RFC 4616)
                if success and credentials.count('\x00') == 2:
                    raw_msg_dec = str(base64.b64decode(raw_msg), 'utf-8')
                    _, user, password = raw_msg_dec.split('\x00')
                    session.add_auth_attempt('plaintext', username=user, password=password)
                    await self.send_message(writer, tag + ' NO Authentication failed')
                else:
                    await self.send_message(writer, tag + ' BAD invalid command')
        else:
            await self.send_message(writer, tag + ' BAD invalid command')
        self.stop_if_too_many_attempts(session)
        return 'Not Authenticated'

    async def cmd_capability(self, session, reader, writer, tag, args):
        await self.send_message(writer, '* CAPABILITY IMAP4rev1 AUTH=PLAIN')
        await self.send_message(writer, tag + ' OK CAPABILITY completed')
        return 'Not Authenticated'

    async def cmd_login(self, session, reader, writer, tag, args):
        if args:
            user_cred = args.split(' ', 1)
        else:
            await self.send_message(writer, tag + ' BAD invalid command')
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
        await self.send_message(writer, tag + ' NO Authentication failed')
        self.stop_if_too_many_attempts(session)
        return 'Not Authenticated'

    async def cmd_logout(self, session, reader, writer, tag, args):
        await self.send_message(writer, '* BYE IMAP4rev1 Server logging out')
        await self.send_message(writer, tag + ' OK LOGOUT completed')
        return 'Logout'

    async def cmd_noop(self, session, reader, writer, tag, args):
        await self.send_message(writer, tag + ' OK NOOP completed')
        return 'Not Authenticated'

    def stop_if_too_many_attempts(self, session):
        if self.max_tries < session.get_number_of_login_attempts():
            session.end_session()

    @staticmethod
    async def send_message(writer, msg):
        message_bytes = bytes(msg + CRLF, 'utf-8')
        writer.write(message_bytes)
        await writer.drain()

    @staticmethod
    def try_b64decode(b64_str, session):
        try:
            result = base64.b64decode(b64_str)
            return True, str(result, 'utf-8')
        except binascii.Error:
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
