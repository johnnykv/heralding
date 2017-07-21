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



import logging
from base64 import b64decode

from aiosmtpd.smtp import SMTP, MISSING, syntax

from heralding.capabilities.handlerbase import HandlerBase

EMPTYSTRING = ""
logger = logging.getLogger(__name__)


class SMTPHandler(SMTP):
    def __init__(self, reader, writer, options, session):
        super().__init__(None)
        self.transport = writer
        self._writer = writer
        self._reader = reader
        self.session = session
        self.session.extended_smtp = None
        self.session.host_name = None
        self.max_tries = int(options['protocol_specific_data']['max_attempts'])
        self.banner = options['protocol_specific_data']['banner']

    @syntax('HELO hostname')
    async def smtp_EHLO(self, hostname):
        await super().smtp_EHLO(hostname)
        await self.push('250-AUTH PLAIN')

    @syntax("AUTH [METHOD]")
    async def smtp_AUTH(self, arg):
        if not self.session.host_name:
            await self.push('503 Error: send EHLO first')
            return
        if not arg:
            await self.push('500 Not enough value')
            return
        args = arg.split(' ')
        if len(args) > 2:
            await self.push('500 Too many values')
            return
        status = await self._call_handler_hook('AUTH', args)
        if status is MISSING:
            method = args[0]
            if method != 'PLAIN':
                await self.push('500 PLAIN method or die')
                return
            blob = None
            if len(args) == 1:
                await self.push('334 ')  # wait client login/password
                line = await self._reader.readline()
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
                    loginpassword = b64decode(blob, validate=True)
                except Exception:
                    await self.push("501 Can't decode base64")
                    return
                try:
                    _, login, password = loginpassword.split(b"\x00")
                except ValueError:  # not enough args
                    await self.push("500 Can't split auth value")
                    return
                self.session.add_auth_attempt('PLAIN', username=str(login, 'utf-8'), password=str(password, 'utf-8'))
                status = '535 Authentication credentials invalid'
        await self.push(status)


class smtp(HandlerBase):
    def __init__(self, options, loop):
        super().__init__(options, loop)
        self._options = options

    async def execute_capability(self, reader, writer, session):
        smtp_cap = SMTPHandler(reader, writer, self._options, session)
        await smtp_cap._handle_client()
