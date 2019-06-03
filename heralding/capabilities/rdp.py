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
from heralding.libs.msrdp.parser import x224ConnectionRequestPDU

logger = logging.getLogger(__name__)

class RDP(HandlerBase):
    async def execute_capability(self, reader, writer, session):
        try:
            await self._handle_session(reader, writer, session)
        except struct.error as exc:
            logger.debug('RDP connection error: %s', exc)
            session.end_session()

    async def _handle_session(self, reader, writer, session):
        address = writer.get_extra_info('peername')[0]
        data = await reader.read(2048)

        # TODO: check if its really a x224CC Request packet
        cr_pdu = x224ConnectionRequestPDU()
        cr_pdu.parse(data)
        logger.debug("CR_PDU: "+str(cr_pdu.pduType)+" "+str(cr_pdu.cookie.decode())+" "+str(cr_pdu.reqProtocols)+" ")

        nego = False
        if cr_pdu.reqProtocols:
                nego = True
        cc_pdu = x224ConnectionConfirmPDU(nego).getFullPacket()
        writer.write(cc_pdu)
        await writer.drain()
        logger.debug("Sent CC_Confirm PDU")

        data = await reader.read(2048)
        logger.debug("Recvd data of size "+ str(len(data))+ " Client data")

        mcs_cres = MCSConnectResponsePDU(3).getFullPacket()
        writer.write(mcs_cres)
        await writer.drain()
        logger.debug("Sent MCS Connect RESponse PDU")

        data = await reader.read(512)
        logger.debug("REceived Attach USER req : "+repr(data))

        session.end_session()
        return


