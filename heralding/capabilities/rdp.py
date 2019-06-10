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

    async def send_data(self,writer, data, tlsObj=None):
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
        address = writer.get_extra_info('peername')[0]
        
        data = await reader.read(2048)
        # TODO: check if its really a x224CC Request packet
        cr_pdu = x224ConnectionRequestPDU()
        cr_pdu.parse(data)
        logger.debug("CR_PDU: "+str(cr_pdu.pduType)+" "+str(cr_pdu.cookie.decode())+" "+str(cr_pdu.reqProtocols)+" ")

        nego = False
        start_tls = True
        if cr_pdu.reqProtocols:
            nego = True
        cc_pdu = x224ConnectionConfirmPDU(nego, start_tls).getFullPacket()
        writer.write(cc_pdu)
        await writer.drain()
        logger.debug("Sent CC_Confirm PDU with TLS")

        tls_obj = None
        if start_tls:
            # TLS start
            logger.debug("TLS initilization")
            tls_obj = TLS(writer, reader,'rdp.pem')
            await tls_obj.do_tls_handshake()

        ## Now use send_data and recv_data

        # data = await reader.read(2048) # DEP
        data = await self.recv_data(reader, 2048, tls_obj)
        logger.debug("Recvd data of size " + str(len(data)) + " Client data")
        # print("CLINET_TLS_DATA: ", repr(data))

        # This packet includes ServerSecurity data
        server_sec = ServerSecurity()
        mcs_cres = MCSConnectResponsePDU(3, server_sec, start_tls).getFullPacket()

        # writer.write(mcs_cres)
        # await writer.drain()
        await self.send_data(writer, mcs_cres, tls_obj)
        logger.debug("Sent MCS Connect Response PDU")

        # data = await reader.read(512)
        data = await self.recv_data(reader, 1024, tls_obj)
        er_len = len(data)
        # TODO: check if erect domain req
        # in tls attach user request and erect domain are not merged together
        logger.debug("Received: ErectDomainRequest and AttactUserRequest(not in tls) : "+repr(data))

        # data = await reader.read(512)
        # if we got only erectdomian req in previous read, len should be less than 13
        if er_len < 13:
            logger.debug("Waiting for Attach USer req")
            # Here , this dosen't occur in rdp_security mode, but it tls mode it keeps waiting for data
            data = await self.recv_data(reader, 1024, tls_obj)
            # # TODO: check if attach user req
            logger.debug("Received: Attach USER req : "+repr(data))

        mcs_usrcnf =MCSAttachUserConfirmPDU().getFullPacket()
        # writer.write(mcs_usrcnf)
        # await writer.drain()
        await self.send_data(writer, mcs_usrcnf, tls_obj)
        logger.debug("Sent: Attach User Confirm")
    
        # Handle multiple Channel Join request PUDs
        for req in range(7):
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

            # writer.write(channel_cnf)
            # await writer.drain()
            await self.send_data(writer, channel_cnf, tls_obj)
            logger.debug("Sent: MCS Channel Join Confirm of channel %s"%(channel_id))

        # Handle Client Security Exchange PDU
        if not data:
            # data = await reader.read(2048)
            data = await self.recv_data(reader, 2048, tls_obj)
        
        print("CLIENT SEC EX: ", repr(data))
        client_sec = ClientSecurityExcahngePDU()
        client_sec.parse(data)
        self.encClientRandom = client_sec.encClientRandom
        print("ENC_CLIENT_RANDOM: ", self.encClientRandom)
        decRandom = server_sec.decryptClientRandom(self.encClientRandom)
        print("DEC_CLIENT_RANDOM: ", decRandom)
        # set client random to serverSec
        server_sec._clientRandom = decRandom

        # Handle Client Info PDU (contains credentials)
        data = await reader.read(2048)
        # print("CLIENT INFO: ", repr(data))
        client_info = ClientInfoPDU()
        client_info.parse(data)
        print("CLIENT_INFO: sig: ", client_info.dataSig)
        print("CLIENT_INFO: ENCADTA: ", client_info.encData)
        decInfo = server_sec.decryptClientInfo(client_info.encData)
        print("CLIENT_DEC_DATA: ", repr(decInfo))

        session.end_session()
