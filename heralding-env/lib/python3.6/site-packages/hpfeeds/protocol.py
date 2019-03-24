# Copyright (C) 2010-2013 Mark Schloesser <ms@mwcollect.org
# This file is part of hpfeeds - https://github.com/rep/hpfeeds
# See the file 'LICENSE' for copying permission.

import hashlib
import struct
import sys

from .exceptions import MessageTooBig, ProtocolException

BUFSIZ = 16384

OP_ERROR = 0
OP_INFO = 1
OP_AUTH = 2
OP_PUBLISH = 3
OP_SUBSCRIBE = 4
OP_UNSUBSCRIBE = 5

MAXBUF = 1024**2

SIZES = {
    OP_ERROR: 5 + MAXBUF,
    OP_INFO: 5 + 256 + 20,
    OP_AUTH: 5 + 256 + 20,
    OP_PUBLISH: 5 + MAXBUF,
}


if sys.version_info[0] == 3:
    binary_type = bytes
    text_type = str
    unicode = str
else:
    binary_type = str
    text_type = unicode


def hashsecret(rand, secret):
    return hashlib.sha1(bytes(rand) + secret.encode('utf-8')).digest()


def force_bytes(value):
    if isinstance(value, text_type):
        return value.encode('utf-8')
    return value


def force_str(value):
    if isinstance(value, str):
        return value
    if isinstance(value, bytearray):
        value = bytes(value)
    if isinstance(value, binary_type):
        return value.decode('utf-8')
    if isinstance(value, text_type):
        return value.encode('utf-8')
    return value


def strpack8(x):
    # packs a string with 1 byte length field
    x = force_bytes(x)
    return struct.pack('!B', len(x)) + x


def strunpack8(x):
    # unpacks a string with 1 byte length field
    length = ord(x[0:1])
    return force_str(x[1:1+length]), x[1+length:]


def msghdr(op, data):
    return struct.pack('!iB', 5 + len(data), op) + data


def msginfo(name, rand):
    return msghdr(OP_INFO, strpack8(name) + force_bytes(rand))


def msgsubscribe(ident, chan):
    return msghdr(OP_SUBSCRIBE, strpack8(ident) + force_bytes(chan))


def msgunsubscribe(ident, chan):
    return msghdr(OP_UNSUBSCRIBE, strpack8(ident) + force_bytes(chan))


def msgpublish(ident, chan, data):
    return msghdr(
        OP_PUBLISH,
        strpack8(ident) + strpack8(chan) + force_bytes(data),
    )


def msgauth(rand, ident, secret):
    return msghdr(OP_AUTH, strpack8(ident) + hashsecret(rand, secret))


def msgerror(error):
    return msghdr(OP_ERROR, force_bytes(error))


def readinfo(data):
    ident, rand = strunpack8(data)
    return force_str(ident), rand


def readauth(data):
    ident, secret = strunpack8(data)
    return force_str(ident), secret


def readsubscribe(data):
    ident, rest = strunpack8(data)
    return force_str(ident), force_str(rest)


def readunsubscribe(data):
    ident, rest = strunpack8(data)
    return force_str(ident), force_str(rest)


def readpublish(data):
    ident, rest = strunpack8(data)
    chan, rest = strunpack8(rest)
    return force_str(ident), force_str(chan), rest


def readerror(error):
    return force_str(error)


class Unpacker(object):

    def __init__(self):
        self.reset()

    def __iter__(self):
        return self

    def __next__(self):
        return self.unpack()

    def next(self):
        # For python2.7 compatibility only
        return self.__next__()

    def reset(self):
        self.buf = bytearray()

    def feed(self, data):
        self.buf.extend(data)

    def ready(self):
        if len(self.buf) < 5:
            return False

        ml, opcode = struct.unpack('!iB', self.buf[0:5])

        if opcode < OP_ERROR or opcode > OP_UNSUBSCRIBE:
            raise ProtocolException('Unknown opcode: {}'.format(opcode))

        max_ml = SIZES.get(opcode, MAXBUF)
        if ml > max_ml:
            raise MessageTooBig(opcode, ml, max_ml)

        if len(self.buf) < ml:
            return False

        return True

    def pop(self):
        ml, opcode = struct.unpack('!iB', self.buf[0:5])
        data = bytes(self.buf[5:][:ml-5])
        del self.buf[:ml]
        return opcode, data

    def unpack(self):
        if not self.ready():
            raise StopIteration('No message')
        return self.pop()
