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

logger = logging.getLogger(__name__)


class InvalidExpectedData(Exception):

  def __init__(self, message=""):
    Exception.__init__(self, message)


class RawBytes():
  """ Read/Consume raw bytes """

  def __init__(self, data, structFormat, typeSize, pos=0, optional=False):
    self.data = data
    self._pos = pos
    self._structFormat = structFormat
    self._typeSize = typeSize
    self._optional = optional

  def dataLen(self):
    return len(self.data[self._pos:])

  def read(self):
    if self.dataLen() < self._typeSize:
      if self._optional:
        logger.debug("No optional data present in the PDU")
        return (b'', self._pos)
      else:
        raise InvalidExpectedData("Bytes Stream is too small to read")
    self.value = struct.unpack(
        self._structFormat, self.data[self._pos:self._pos + self._typeSize])[0]
    self._pos += self._typeSize

    return self.value, self._pos

  def readRaw(self):
    if self.dataLen() < self._typeSize:
      if self._optional:
        logger.debug("No optional data present in the PDU")
        return (b'', self._pos)
      else:
        raise InvalidExpectedData("Bytes Stream is too small to read")
    self.value = self.data[self._pos:self._pos + self._typeSize]
    self._pos += self._typeSize

    return self.value, self._pos

  def readUntil(self, until):
    if self.dataLen() < len(until) + 1:
      if self._optional:
        logger.debug("No optional data present in the PDU")
        return (b'', self._pos)
      else:
        raise InvalidExpectedData("Bytes Stream is too small to read")
    self.value = b''
    _data = self.data[self._pos:self._pos + len(until) + 1]
    while _data[-len(until):] != until:
      i = _data[0]
      self.value += i.to_bytes(1, byteorder='big')
      self._pos += 1
      _data = self.data[self._pos:self._pos + len(until) + 1]

    # insert the last char before mactching bytes
    i = _data[0]
    self.value += i.to_bytes(1, byteorder='big')
    self._pos += 1

    self._pos += len(until)
    return self.value, self._pos


class UInt8(RawBytes):

  def __init__(self, data, pos, optional=False):
    RawBytes.__init__(self, data, "B", 1, pos, optional)


class SInt8(RawBytes):

  def __init__(self, data, pos, optional=False):
    RawBytes.__init__(self, data, "b", 1, pos, optional)


class UInt16Be(RawBytes):

  def __init__(self, data, pos, optional=False):
    RawBytes.__init__(self, data, ">H", 2, pos, optional)


class UInt16Le(RawBytes):

  def __init__(self, data, pos, optional=False):
    RawBytes.__init__(self, data, "<H", 2, pos, optional)


class UInt32Be(RawBytes):

  def __init__(self, data, pos, optional=False):
    RawBytes.__init__(self, data, ">I", 4, pos, optional)


class UInt32Le(RawBytes):

  def __init__(self, data, pos, optional=False):
    RawBytes.__init__(self, data, "<I", 4, pos, optional)


class tpktPDUParser():

  def __init__(self):
    # only length can be uselful
    self.length = None

  def parse(self, raw_data, pos=0):
    """Returs pos of the rest of the payload"""
    _, pos = RawBytes(raw_data, None, 2,
                      pos).readRaw()  # consume version and reserved
    self.length, pos = UInt16Be(raw_data, pos).read()
    return pos


class x224DataPDU():

  @classmethod
  def parse(cls, raw_data, pos):
    """Returns the pos of the rest of the Payload"""
    _, pos = RawBytes(raw_data, None, 3, pos).readRaw()
    return pos


class x224ConnectionRequestPDU():
  # length            1byte
  # pdutype/credit    1byte
  # dst_ref           2byte
  # src_ref           2byte
  # options           1byte

  def __init__(self):
    # only pdu type is required
    self.pduType = None
    self.cookie = None
    self.reqProtocols = False

  def parse(self, raw_data, pos=0):
    pos = tpktPDUParser().parse(raw_data, 0)
    self.pduType, pos = UInt8(raw_data, pos + 1).read()  # ignore lenght byte
    _, pos = RawBytes(raw_data, None, 5, pos).readRaw()  # consume 5bytes
    # cookie is optional
    if b"Cookie: mstshash=" in raw_data:
      self.cookie, pos = RawBytes(raw_data, None, None,
                                  pos).readUntil(b"\x0d\x0a")
    # parse nego req if present
    if raw_data[pos:] != b'':
      _, pos = RawBytes(raw_data, None, 4, pos).readRaw()
      self.reqProtocols, pos = UInt32Le(raw_data, pos).read()

    return pos


class MCSChannelJoinRequestPDU():

  def __init__(self):
    self.header = None
    self.initiator = None
    self.channelID = None

  def parse(self, raw_data, pos=0):
    pos = tpktPDUParser().parse(raw_data, 0)
    pos = x224DataPDU().parse(raw_data, pos)
    self.header, pos = RawBytes(raw_data, None, 1, pos).readRaw()
    if self.header != b'\x38':
      return -1

    self.initiator, pos = UInt16Be(raw_data, pos).read()
    self.channelID, pso = UInt16Be(raw_data, pos).read()
    return pos


class ErectDomainRequestPDU():

  @staticmethod
  def checkPDU(raw_data, pos=0):
    # Type constant of ErectDomainRequest
    ERECT_DOMAIN_REQUEST = 1

    pos = tpktPDUParser().parse(raw_data, 0)
    pos = x224DataPDU().parse(raw_data, pos)
    pdu_type, pos = UInt8(raw_data, pos).read()

    if pdu_type == (ERECT_DOMAIN_REQUEST << 2):
      return True

    return False


class AttachUserRequestPDU():

  @staticmethod
  def checkPDU(raw_data, pos=0):
    # Type constant of AttachUserRequest
    ATTACH_USER_REQUEST = 10

    pos = tpktPDUParser().parse(raw_data, 0)
    pos = x224DataPDU().parse(raw_data, pos)
    pdu_type, pos = UInt8(raw_data, pos).read()

    if pdu_type == (ATTACH_USER_REQUEST << 2):
      return True

    return False


class ClientSecurityExcahngePDU():

  def __init__(self):
    self.secHeaderFlags = None
    self.secPacketLen = None
    self.encClientRandom = None

  def parse(self, raw_data, pos=0):
    pos = tpktPDUParser().parse(raw_data, 0)
    pos = x224DataPDU().parse(raw_data, pos)
    _, pos = RawBytes(raw_data, None, 8, pos).readRaw()  # 7 changed to 8
    self.secHeaderFlags, pos = UInt16Le(raw_data, pos).read()
    # +2 for skipkking bytes read
    self.secPacketLen, pos = UInt32Le(raw_data, pos + 2).read()
    # not reading last 8byte padding
    self.encClientRandom, pos = RawBytes(raw_data, None, self.secPacketLen - 8,
                                         pos).readRaw()
    return pos


class ClientInfoPDU():

  def __init__(self):
    self.secHeaderFlags = None
    self.infoLen = None
    self.dataSig = None
    self.encData = None

    # from decrypted data
    self.rdpUsername = None
    self.rdpPassword = None

  def parseTLS(self, raw_data, pos=0):
    pos = tpktPDUParser().parse(raw_data, 0)
    pos = x224DataPDU().parse(raw_data, pos)
    _, pos = RawBytes(raw_data, None, 6, pos).readRaw()
    # read length bytes (PER encoded)
    _infoLen, pos = UInt16Be(raw_data, pos).read()
    self.infoLen = _infoLen & 0x0fff
    # consume flags(2), flagsHi(2), CodePage(4), OptionalFlags(4)
    _, pos = RawBytes(raw_data, None, 12, pos).readRaw()
    #  cbParams(2+2+2+2+2)
    cbDomain, pos = UInt16Le(raw_data, pos).read()
    cbUsername, pos = UInt16Le(raw_data, pos).read()
    cbPassword, pos = UInt16Le(raw_data, pos).read()
    cbAltShell, pos = UInt16Le(raw_data, pos).read()
    cbWorkDir, pos = UInt16Le(raw_data, pos).read()
    # mandatory NULL terminator for all cbPrams is 2 bytes
    Domain, pos = RawBytes(raw_data, None, cbDomain + 2, pos).readRaw()
    Username, pos = RawBytes(raw_data, None, cbUsername + 2, pos).readRaw()
    Password, pos = RawBytes(raw_data, None, cbPassword + 2, pos).readRaw()
    AltShell, pos = RawBytes(raw_data, None, cbAltShell + 2, pos).readRaw()
    WorkDir, pos = RawBytes(raw_data, None, cbWorkDir + 2, pos).readRaw()

    # strip the last two null bytes
    self.rdpUsername = Username.decode('utf-16', 'ignore')[:-1]
    self.rdpPassword = Password.decode('utf-16', 'ignore')[:-1]
    return pos
