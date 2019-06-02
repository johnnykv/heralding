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
                print("No optional data present")
                return (b'', self._pos)
            else:
                raise Exception("Bytes Stream is too small to read")
        self.value = struct.unpack(self._structFormat, self.data[self._pos:self._pos+self._typeSize])[0]
        self._pos += self._typeSize

        return self.value, self._pos

    def readRaw(self):
        if self.dataLen() < self._typeSize:
            if self._optional:
                print("No optional data present")
                return (b'', self._pos)
            else:
                raise Exception("Bytes Stream is too small to read")
        self.value = self.data[self._pos:self._pos+self._typeSize]
        self._pos += self._typeSize

        return self.value, self._pos

    def readUntil(self, until):
        if self.dataLen() < len(until)+1:
            if self._optional:
                print("No optional data present")
                return (b'', self._pos)
            else:
                raise Exception("Bytes Stream is too small to read")
        self.value = b''
        _data = self.data[self._pos:self._pos+len(until)+1]
        while _data[-len(until):] != until:
            print(repr(_data))
            i = _data[0]
            self.value += i.to_bytes(1, byteorder='big')
            self._pos += 1
            _data = self.data[self._pos:self._pos+len(until)+1]

        # insert the char before mactching bytes
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
        _, pos = RawBytes(raw_data, None, 2, pos).readRaw()  # consume version and reserved
        self.length, pos = UInt16Be(raw_data, pos).read()
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
        self.pduType, pos = UInt8(raw_data, pos+1).read()  # ignore lenght byte
        _, pos = RawBytes(raw_data, None, 5, pos).readRaw()  # consume 5bytes
        self.cookie, pos = RawBytes(raw_data, None, None, pos).readUntil(b"\x0d\x0a")
        # parse nego req if present
        print(raw_data[pos:])
        if raw_data[pos:] != b'':
            _, pos = RawBytes(raw_data, None, 4, pos).readRaw()
            self.reqProtocols, pos = UInt32Le(raw_data, pos).read()

        return pos
