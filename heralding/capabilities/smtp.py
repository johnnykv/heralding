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
import socket
import asyncio
import logging
import aiosmtpd

from aiosmtpd.smtp import SMTP, MISSING, syntax

from heralding.capabilities.handlerbase import HandlerBase

log = logging.getLogger(__name__)
aiosmtpd.smtp.log = log


class SMTPHandler(SMTP):
    def __init__(self, reader, writer, session, options, loop):
        self.banner = options['protocol_specific_data']['banner']
        super().__init__(None, hostname=self.banner, loop=loop)
        # Reset standard banner.
        self.__ident__ = ""
        self._reader = reader
        self._writer = writer
        self.transport = writer
        self.fqdn = socket.getfqdn()

        self._set_rset_state()
        self.session = session
        self.session.peer = self.transport.get_extra_info('peername')
        self.session.extended_smtp = None
        self.session.host_name = None

    async def push(self, status):
        response = bytes(
            status + '\r\n', 'utf-8' if self.enable_SMTPUTF8 else 'ascii')
        self._writer.write(response)
        log.debug(response)
        try:
            await self._writer.drain()
        except ConnectionResetError:
            self.stop()

    async def _handle_client(self):
        log.debug('%r handling connection', self.session.peer)
        await self.push('220 {} {}'.format(self.hostname, self.__ident__))
        while self.transport is not None:   # pragma: nobranch
            # XXX Put the line limit stuff into the StreamReader?
            try:
                try:
                    line = await self._reader.readline()
                except ConnectionResetError:
                    self.transport.close()
                    break
                log.debug('_handle_client readline: %s', line)
                # XXX this rstrip may not completely preserve old behavior.
                line = line.rstrip(b'\r\n')
                log.debug('%r Data: %s', self.session.peer, line)
                if not line:
                    await self.push('500 Error: bad syntax')
                    continue
                i = line.find(b' ')
                # Decode to string only the command name part, which must be
                # ASCII as per RFC.  If there is an argument, it is decoded to
                # UTF-8/surrogateescape so that non-UTF-8 data can be
                # re-encoded back to the original bytes when the SMTP command
                # is handled.
                if i < 0:
                    command = line.upper().decode(encoding='ascii')
                    arg = None
                else:
                    command = line[:i].upper().decode(encoding='ascii')
                    arg = line[i+1:].strip()
                    # Remote SMTP servers can send us UTF-8 content despite
                    # whether they've declared to do so or not.  Some old
                    # servers can send 8-bit data.  Use surrogateescape so
                    # that the fidelity of the decoding is preserved, and the
                    # original bytes can be retrieved.
                    if self.enable_SMTPUTF8:
                        arg = str(
                            arg, encoding='utf-8', errors='surrogateescape')
                    else:
                        try:
                            arg = str(arg, encoding='ascii', errors='strict')
                        except UnicodeDecodeError:
                            # This happens if enable_SMTPUTF8 is false, meaning
                            # that the server explicitly does not want to
                            # accept non-ASCII, but the client ignores that and
                            # sends non-ASCII anyway.
                            await self.push('500 Error: strict ASCII mode')
                            # Should we await self.handle_exception()?
                            continue
                max_sz = (self.command_size_limits[command]
                          if self.session.extended_smtp
                          else self.command_size_limit)
                if len(line) > max_sz:
                    await self.push('500 Error: line too long')
                    continue
                if not self._tls_handshake_okay and command != 'QUIT':
                    await self.push(
                        '554 Command refused due to lack of security')
                    continue
                if (self.require_starttls
                        and not self._tls_protocol
                        and command not in ['EHLO', 'STARTTLS', 'QUIT']):
                    # RFC3207 part 4
                    await self.push('530 Must issue a STARTTLS command first')
                    continue
                method = getattr(self, 'smtp_' + command, None)
                if method is None:
                    await self.push(
                        '500 Error: command "%s" not recognized' % command)
                    continue
                await method(arg)
            except asyncio.CancelledError:
                # The connection got reset during the DATA command.
                # XXX If handler method raises ConnectionResetError, we should
                # verify that it was actually self._reader that was reset.
                log.debug('Connection lost during _handle_client()')
                self._writer.close()
                raise
            except Exception as error:
                try:
                    status = await self.handle_exception(error)
                    await self.push(status)
                except Exception as error:
                    try:
                        log.exception('Exception in handle_exception()')
                        status = '500 Error: ({}) {}'.format(
                            error.__class__.__name__, str(error))
                    except Exception:
                        status = '500 Error: Cannot describe error'
                    await self.push(status)

    @syntax("AUTH mechanism [initial-response]")
    async def smtp_AUTH(self, arg):
        if not arg:
            await self.push('500 Not enough value')
            return
        args = arg.split()
        if len(args) > 2:
            await self.push('500 Too many values')
            return
        mechanism = args[0]
        if mechanism == 'PLAIN':
            if len(args) == 1:
                await self.push('334 ')  # wait for client login/password
                line = await self.readline()
                if not line:
                    return
                blob = line.strip()
            else:
                blob = args[1].encode()

            try:
                loginpassword = base64.b64decode(blob)
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
            if len(args) > 1:
                username = str(base64.b64decode(args[1]), 'utf-8')
                await self.push('334 ' + str(base64.b64encode(b'Password:'), 'utf-8'))

                password_bytes = await self.readline()
                if not password_bytes:
                    return
                password = str(base64.b64decode(password_bytes), 'utf-8')
                self.session.add_auth_attempt('LOGIN', username=username, password=password)
            else:
                await self.push('334 ' + str(base64.b64encode(b'Username:'), 'utf-8'))

                username_bytes = await self.readline()
                if not username_bytes:
                    return

                await self.push('334 ' + str(base64.b64encode(b'Password:'), 'utf-8'))

                password_bytes = await self.readline()
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

            credentials_bytes = await self.readline()
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
            await self.push('500 incorrect AUTH mechanism')
            return
        status = '535 authentication failed'
        await self.push(status)

    @syntax('QUIT')
    async def smtp_QUIT(self, arg):
        if arg:
            await self.push('501 Syntax: QUIT')
        else:
            status = await self._call_handler_hook('QUIT')
            await self.push('221 Bye' if status is MISSING else status)
            self.stop()

    async def readline(self):
        line = b''
        try:
            line = await self._reader.readline()
        except ConnectionResetError:
            self.stop()
        else:
            return line

    def stop(self):
        self.transport.close()
        self.transport = None


class smtp(HandlerBase):
    def __init__(self, options, loop):
        super().__init__(options, loop)
        self.loop = loop
        self._options = options

    async def execute_capability(self, reader, writer, session):
        smtp_cap = SMTPHandler(reader, writer, session, self._options, self.loop)
        await smtp_cap._handle_client()
