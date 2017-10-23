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

import os
import logging

from heralding.capabilities.handlerbase import HandlerBase

# VNC constants
RFB_VERSION = b'RFB 003.007\n'
SUPPORTED_AUTH_METHODS = b'\x01\x02'
VNC_AUTH = b'\x02'
AUTH_FAILED = b'\x00\x00\x00\x01'

logger = logging.getLogger(__name__)


class Vnc(HandlerBase):
    def __init__(self, options, loop):
        super().__init__(options, loop)

    async def execute_capability(self, reader, writer, session):
        await self._handle_session(session, reader, writer)

    async def _handle_session(self, session, reader, writer):
        writer.write(RFB_VERSION)
        client_version = await reader.read(1024)

        if client_version and client_version == RFB_VERSION:
            await self.security_handshake(reader, writer, session)
        else:
            session.end_session()

    async def security_handshake(self, reader, writer, session):
        writer.write(SUPPORTED_AUTH_METHODS)
        sec_method = await reader.read(1024)

        if sec_method and sec_method == VNC_AUTH:
            await self.do_vnc_authentication(reader, writer, session)
        else:
            session.end_session()

    async def do_vnc_authentication(self, reader, writer, session):
        challenge = os.urandom(16)
        writer.write(challenge)
        client_response_ = await reader.read(1024)

        # session.add_auth_attempt('des_challenge', response=client_response_)

        print('challenge: {}; response: {}\n'.format(challenge, client_response_))
        writer.write(AUTH_FAILED)
        session.end_session()
