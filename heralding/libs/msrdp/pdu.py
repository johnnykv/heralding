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

# *** This file contains all the PDU required for RDP Protocol ***
# each top tier PDU class will have a payload and generate method

from .packer import Uint16BE, Int16BE, Uint32LE, Uint32BE
from .parser import x224ConnectionRequestPDU
from .security import ServerSecurity

    
class tpktPDU:
    def __init__(self, payload):
        self.version = 3
        self.reserved = 0
        self.payload = payload

    def generate(self):
        payload_len = Int16BE.pack(1+1+2+len(self.payload))
        # print(repr(payload_len))
        return bytes([self.version, self.reserved])+payload_len+self.payload


class x224DataPDU:
    @staticmethod
    def generate():
        return b'\x02\xf0\x80'


class x224ConnectionConfirmPDU():
    def __init__(self, nego=False, tls=False):
        self.type = b'\xd0'
        self.dest_ref = b'\x00\x00'  # 0 bytes
        self.src_ref = b'\x12\x34'  # bogus value
        self.options = b'\x00'
        self.nego = nego
        self.is_tls = tls

    def generate(self):
        data = self.type+self.dest_ref+self.src_ref+self.options
        len_indicator = len(data)  # 1byte length of PDU without indicator byte

        if self.nego:
            if self.is_tls:
                nego_res = b'\x02\x00\x08\x00'+b'\x01' +bytes(3)  # TLS security
            else:
                nego_res = b'\x02\x00\x08\x00'+b'\x00' +bytes(3)  # RDP security
            len_indicator += len(nego_res)
            data += nego_res

        return bytes([len_indicator])+data

    def getFullPacket(self):
        return tpktPDU(self.generate()).generate()


class ServerData:
    @classmethod
    def generate(cls, cReqproto, serverSec, is_tls=False):
        # Servr Core data
        coreData_1 = b'\x01\x0c\x0c\x00\x04\x00\x08\x00'
        clientReqPro = Uint32LE.pack(cReqproto)

        # ServerNetwork Data
        netData = b'\x03\x0c\x08\x00\xeb\x03\x00\x00'  # here channel count 0

        # ServerSec Data
        # here choosing encryption of 128bit by default method \x02\x00\x00\x00
        if is_tls:
            part_1 = b'\x02\x0c\xec\x00\x00\x00\x00\x00\x00\x00\x00\x00\x20\x00\x00\x00\xb8\x00\x00\x00'
        else:
            part_1 = b'\x02\x0c\xec\x00\x02\x00\x00\x00\x03\x00\x00\x00\x20\x00\x00\x00\xb8\x00\x00\x00'
        serverRandom = ServerSecurity.SERVER_RANDOM

        # an instance of ServerSecurity class required
        certData = serverSec.getServerCertBytes()
        #ADD all
        serverCoreData = coreData_1+clientReqPro
        serverNetData = netData
        # serverSecData = part_1+serverRandom+pubkeyProps_1+pubkeyProps_2+pubExp+modulus+sigBlobProps+sigBlob
        serverSecData = part_1+serverRandom+certData

        return serverCoreData+serverNetData+serverSecData


class MCSConnectResponsePDU():
    """ Server MCS Connect Response PDU with GCC Conference Create Response """

    def __init__(self, cReqproto, serverSec, is_tls=False):
        self.cReqproto = cReqproto
        self.serverSec = serverSec
        self.is_tls = is_tls

    def generate(self):
        serverData = ServerData.generate(self.cReqproto, self.serverSec, self.is_tls)
        serverDataLen = Uint16BE.pack(len(serverData) | 0x8000)
        gccCreateRes = b'\x00\x05\x00\x14\x7c\x00\x01\x2a\x14\x76\x0a\x01\x01\x00\x01\xc0\x00\x4d\x63\x44\x6e'
        cc_userDataLen = Uint16BE.pack(len(serverData)+2+len(gccCreateRes))
        cc_userData_1 = b'\x04\x82'
        domainParams = b'\x30\x1a\x02\x01\x22\x02\x01\x03\x02\x01\x00\x02\x01\x01\x02\x01\x00\x02\x01\x01\x02\x03\x00\xff\xf8\x02\x01\x02'
        cc_res = b'\x0a\x01\x00\x02\x01\x00'
        berLen = Uint16BE.pack(len(cc_res)+len(domainParams)+2+2+len(serverData)+2+len(gccCreateRes))
        bertype = b'\x7f\x66\x82'

        return bertype+berLen+cc_res+domainParams+cc_userData_1+cc_userDataLen+gccCreateRes+serverDataLen+serverData

    def getFullPacket(self):
        return tpktPDU(x224DataPDU.generate()+self.generate()).generate()


class MCSAttachUserConfirmPDU():
    def generate(self):
        return b'\x2e\x00\x00\x06'

    # This is full static but just to be sillimar to other methods
    def getFullPacket(self):
        return tpktPDU(x224DataPDU.generate()+self.generate()).generate()


class MCSChannelJoinConfirmPDU():
    def __init__(self, initiator, channelID):
        self.initiator = Uint16BE.pack(initiator)
        self.channelID = Uint32BE.pack(channelID)

    def generate(self):
        res = b'\x3e\x00'
        return res+self.initiator+self.channelID+self.channelID

    def getFullPacket(self):
        return tpktPDU(x224DataPDU.generate()+self.generate()).generate()

