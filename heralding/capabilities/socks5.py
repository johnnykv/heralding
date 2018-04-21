# Copyright (C) 2018 Roman Samoilenko <ttahabatt@gmail.com>
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

from heralding.capabilities.handlerbase import HandlerBase

# Socks constants
SOCKS_VERSION = b'\x05'
AUTH_METHOD = b'\x02'  # username/password authentication. RFC 1929
SOCKS_FAIL = b'\xFF'

logger = logging.getLogger(__name__)


class Socks5(HandlerBase):
    async def execute_capability(self, reader, writer, session):
        await self._handle_session(reader, writer, session)

    async def _handle_session(self, reader, writer, session):
        # 257 - max bytes number for greeting according to RFC 1928
        greeting = await reader.read(257)
        if len(greeting) > 2:
            await self.try_authenticate(reader, writer, session, greeting)
        else:
            logger.debug("Incorrect client greeting string: %r" % greeting)
        session.end_session()

    async def try_authenticate(self, reader, writer, session, greeting):
        version, authmethods = self.unpack_msg(greeting)
        if version == SOCKS_VERSION:
            if AUTH_METHOD in authmethods:
                await self.do_authenticate(reader, writer, session)
            else:
                writer.write(SOCKS_VERSION + SOCKS_FAIL)
                await writer.drain()
        else:
            logger.debug("Wrong socks version: %r" % version)

    async def do_authenticate(self, reader, writer, session):
        writer.write(SOCKS_VERSION + AUTH_METHOD)
        await writer.drain()
        # 513 - max bytes number for username/password auth according to RFC 1929
        auth_data = await reader.read(513)
        if len(auth_data) > 4:
            username, password = self.unpack_auth(auth_data)
            session.add_auth_attempt('plaintext', username=username.decode(),
                                     password=password.decode())
            writer.write(AUTH_METHOD + SOCKS_FAIL)
            await writer.drain()
        else:
            logger.debug("Wrong authentication data: %r" % auth_data)

    @staticmethod
    def unpack_msg(data):
        socks_version = data[:1]  # we need byte representation
        authmethods_n = data[1]
        authmethods = data[2:2+authmethods_n]
        return socks_version, authmethods

    @staticmethod
    def unpack_auth(auth_data):
        ulen = auth_data[1]
        username = auth_data[2:2+ulen]
        plen = auth_data[2+ulen:2+ulen+1][0]
        password = auth_data[-plen:]
        return username, password
