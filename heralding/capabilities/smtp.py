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

# Parts of this code are from secure-smtpd (https://github.com/bcoe/secure-smtpd)

# Aniket Panse <contact@aniketpanse.in> grants Johnny Vestergaard <jkv@unixcluster.dk>
# a perpetual, worldwide, non-exclusive, no-charge, royalty-free, irrevocable
# copyright license to reproduce, prepare derivative works of, publicly
# display, publicly perform, sublicense, relicense, and distribute [the] Contributions
# and such derivative works.

import time
import random
import base64
import asyncio
import socket
import logging

from aiosmtpd.smtp import SMTP, MISSING, syntax

from heralding.capabilities.handlerbase import HandlerBase

log = logging.getLogger(__name__)


class SMTPHandler(SMTP):
    def __init__(self, reader, writer, options, session, loop):
        self.banner = options['protocol_specific_data']['banner']
        super().__init__(None, hostname=self.banner, loop=loop)
        self.__ident__ = ""
        self._reader = reader
        self._writer = writer
        self.transport = writer
        self.session = session
        self.loop = loop
        self.fqdn = socket.getfqdn()
        self.session.peer = self.transport.get_extra_info('peername')
        self.session.extended_smtp = None
        self.session.host_name = None


    @syntax("AUTH mechanism [initial-response]")
    async def smtp_AUTH(self, arg):
        if not arg:
            await self.push('500 Not enough value')
            return
        args = arg.split(' ')
        if len(args) > 2:
            await self.push('500 Too many values')
            return
        status = await self._call_handler_hook('AUTH', args)
        if status is MISSING:
            mechanism = args[0]
            if mechanism == 'PLAIN':
                if len(args) == 1:
                    await self.push('334 ')  # wait for client login/password
                    line = await self._reader.readline()
                    if not line: # Attention!
                        return
                    blob = line.strip()
                    if blob.decode() == '*':
                        await self.push("501 Auth aborted")
                        return
                else:
                    blob = args[1].encode()

                if blob == b'=':
                    login = None
                    password = None
                else:
                    try:
                        loginpassword = base64.b64decode(blob, validate=True)
                    except Exception:
                        await self.push("501 Can't decode base64")
                        return
                    try:
                        _, login, password = loginpassword.split(b"\x00")
                    except ValueError:  # not enough args
                        await self.push("500 Can't split auth value")
                        return
                    self.session.add_auth_attempt('PLAIN', username=str(login, 'utf-8'),
                                                  password=str(password, 'utf-8'))
            elif mechanism == 'LOGIN':
                if len(args) == 2:
                    username = str(base64.b64decode(args[1]), 'utf-8')
                    await self.push('334 ' + str(base64.b64encode(b'Password:'), 'utf-8'))
                    password_bytes = await self._reader.readline()
                    if not password_bytes:
                        return
                    password = str(base64.b64decode(password_bytes), 'utf-8')
                    self.session.add_auth_attempt('LOGIN', username=username, password=password)
                else:
                    await self.push('334 ' + str(base64.b64encode(b'Username:'), 'utf-8'))
                    username_bytes = await self._reader.readline()
                    if not username_bytes:
                        return
                    await self.push('334 ' + str(base64.b64encode(b'Password:'), 'utf-8'))
                    password_bytes = await self._reader.readline()
                    if not password_bytes:
                        return
                    self.session.add_auth_attempt('LOGIN', username=str(base64.b64decode(username_bytes), 'utf-8'),
                                                  password=str(base64.b64decode(password_bytes), 'utf-8'))
            elif mechanism == 'CRAM-MD5':
                r = random.randint(5000, 20000)
                t = int(time.time())

                # challenge is of the form '<24609.1047914046@awesome.host.com>'
                self.sent_cram_challenge = "<" + str(r) + "." + str(t) + "@" + self.fqdn + ">"
                cram_challenge_bytes = bytes(self.sent_cram_challenge, 'utf-8')
                await self.push("334 " + str(base64.b64encode(cram_challenge_bytes), 'utf-8'))

                credentials_bytes = await self._reader.readline()
                if not credentials_bytes:
                    return
                credentials = str(base64.b64decode(credentials_bytes), 'utf-8')
                if self.sent_cram_challenge is None or ' ' not in credentials:
                    await self.push('451 Internal confusion')
                    return
                username, digest = credentials.split()
                self.session.add_auth_attempt('cram_md5', username=username, password=digest,
                                               challenge=self.sent_cram_challenge)
                await self.push('535 authentication failed')
            else:
                await self.push('500 method or die')  # TO FINISH
                return
        status = '535 Authentication credentials invalid'
        await self.push(status)

    @syntax('QUIT')
    async def smtp_QUIT(self, arg):
        if arg:
            await self.push('501 Syntax: QUIT')
        else:
            status = await self._call_handler_hook('QUIT')
            await self.push('221 Bye' if status is MISSING else status)
            self.transport.close()

    async def push(self, status): # TODO: It must be changed is the future.
        response = bytes(
            status + '\r\n', 'utf-8' if self.enable_SMTPUTF8 else 'ascii')
        self._writer.write(response)
        log.debug(response)
        # await self._writer.drain()

class smtp(HandlerBase):
    def __init__(self, options, loop):
        super().__init__(options, loop)
        self.loop = loop
        self._options = options

    async def execute_capability(self, reader, writer, session):
        smtp_cap = SMTPHandler(reader, writer, self._options, session, self.loop)
        await smtp_cap._handle_client()
