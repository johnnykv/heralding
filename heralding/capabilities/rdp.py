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
from heralding.libs.msrdp.pdu import x224ConnectionConfirmPDU, MCSConnectResponsePDU, MCSAttachUserConfirmPDU, MCSChannelJoinConfirmPDU
from heralding.libs.msrdp.parser import x224ConnectionRequestPDU, MCSChannelJoinRequestPDU, ClientSecurityExcahngePDU, ClientInfoPDU
from heralding.libs.msrdp.parser import ErectDomainRequestPDU
from heralding.libs.msrdp.security import ServerSecurity
from heralding.libs.msrdp.tls import TLS
logger = logging.getLogger(__name__)


class RDP(HandlerBase):
    async def recv_data(self, reader, size, tlsObj=None):
        if tlsObj:
            data = await tlsObj.read_tls(size)
            return data
        data = await reader.read(size)
        return data

    async def send_data(self, writer, data, tlsObj=None):
        if tlsObj:
            await tlsObj.write_tls(data)
            return
        writer.write(data)
        await writer.drain()
        return

    async def execute_capability(self, reader, writer, session):
        try:
            await self._handle_session(reader, writer, session)
        except struct.error as exc:
            logger.debug('RDP connection error: %s', exc)
            session.end_session()

    async def _handle_session(self, reader, writer, session):
        data = await reader.read(2048)
        cr_pdu = x224ConnectionRequestPDU()
        cr_pdu.parse(data)

        start_tls = True  # this forces tls security
        client_reqProto = 1  # set default to tls
        if cr_pdu.reqProtocols:
            client_reqProto = cr_pdu.reqProtocols
        else:
            # if no nego request was made, then it is rdp security
            client_reqProto = 0

        cc_pdu_obj = x224ConnectionConfirmPDU(client_reqProto, start_tls)
        cc_pdu = cc_pdu_obj.getFullPacket()
        writer.write(cc_pdu)
        await writer.drain()
        if cc_pdu_obj.sentNegoFail:
            logger.debug("Sent x224 RDP Negotiation Failure PDU")
            session.end_session()
            return
        logger.debug("Sent x244CLinetConnectionConfirm PDU")

        tls_obj = None
        if start_tls:
            # TLS Upgrade start
            logger.debug("RDP TLS initilization")
            tls_obj = TLS(writer, reader, 'rdp.pem')
            await tls_obj.do_tls_handshake()

        # Now using send_data and recv_data
        data = await self.recv_data(reader, 2048, tls_obj)
        logger.debug("Recvd data of size " + str(len(data)) + " Client data")

        # This packet includes ServerSecurity data
        server_sec = ServerSecurity()
        mcs_cres = MCSConnectResponsePDU(client_reqProto, server_sec, start_tls).getFullPacket()

        await self.send_data(writer, mcs_cres, tls_obj)
        logger.debug("Sent MCS Connect Response PDU")

        if tls_obj:
            data = await self.recv_data(reader, 41, tls_obj)
        else:
            data = await self.recv_data(reader, 512, tls_obj)

        if not data:
            logger.debug("Expected ErectDomainRequest. Got Nothing.")
            return
        if not ErectDomainRequestPDU.checkPDU(data):
            logger.debug("Malformed Packet Received. Expected ErectDomainRequest.")
            session.end_session()
            return

        # in tls attach user request and erect domain are not merged together
        logger.debug("Received: ErectDomainRequest and AttactUserRequest(not in tls) : "+repr(data))

        er_len = len(data)
        # if we got only erectdomian req in previous read, len should be less than 13
        if er_len < 13:
            # Here , this dosen't occur in rdp_security mode, but it tls mode it keeps waiting for data
            data = await self.recv_data(reader, 64, tls_obj)
            # # TODO: check if attach user req
            logger.debug("Received: Attach USER req : "+repr(data))

        mcs_usrcnf = MCSAttachUserConfirmPDU().getFullPacket()
        await self.send_data(writer, mcs_usrcnf, tls_obj)
        logger.debug("Sent: Attach User Confirm")

        # Handle multiple Channel Join request PUDs
        for _ in range(7):
            # data = await reader.read(2048)
            data = await self.recv_data(reader, 2048, tls_obj)
            if not data:
                logger.debug("Expected: Channel Join/Client Security Packet.Got Nothing.")
                return
            channel_req = MCSChannelJoinRequestPDU()
            v = channel_req.parse(data)
            if v < 0:
                break
            channel_id = channel_req.channelID
            channel_init = channel_req.initiator
            channel_cnf = MCSChannelJoinConfirmPDU(channel_init, channel_id).getFullPacket()

            await self.send_data(writer, channel_cnf, tls_obj)
            logger.debug("Sent: MCS Channel Join Confirm of channel %s" % (channel_id))

        # Handle Client Security Exchange PDU
        if not data:
            # data = await reader.read(2048)
            data = await self.recv_data(reader, 2048, tls_obj)

        # There is no client security exchange in TLS Security
        if tls_obj:
            client_info = ClientInfoPDU()
            client_info.parseTLS(data)
            username = client_info.rdpUsername
            password = client_info.rdpPassword
            session.add_auth_attempt('plaintext', username=username, password=password)

        else:
            client_sec = ClientSecurityExcahngePDU()
            client_sec.parse(data)
            self.encClientRandom = client_sec.encClientRandom
            decRandom = server_sec.decryptClientRandom(self.encClientRandom)
            # set client random to serverSec
            server_sec._clientRandom = decRandom

            # Handle Client Info PDU (contains credentials)

            data = await self.recv_data(reader, 2048, tls_obj)
            client_info = ClientInfoPDU()
            client_info.parse(data)
            decInfo = server_sec.decryptClientInfo(client_info.encData)

        session.end_session()
