# Copyright (C) 2019 Sudipta Pandit <realsdx@protonmail.com>
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

import struct
import logging

from heralding.capabilities.handlerbase import HandlerBase
from heralding.libs.msrdp.pdu import x224ConnectionConfirmPDU, MCSConnectResponsePDU

logger = logging.getLogger(__name__)

class RDP(HandlerBase):
    async def execute_capability(self, reader, writer, session):
        try:
            await self._handle_session(reader, writer, session)
        except struct.error as exc:
            logger.debug('RDP connection error: %s', exc)
            session.end_session()

    async def _handle_session(self, reader, writer, session):
        pass