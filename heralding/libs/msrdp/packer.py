import struct

class Integer:
    FORMAT = ""

    @classmethod
    def pack(cls, value):
        data_bytes = struct.pack(cls.FORMAT, value)

        return data_bytes

# 8 bits
class Int8(Integer):
    FORMAT = "<b"

class Uint8(Integer):
    FORMAT = "<B"

# 16 bits
class Int16LE(Integer):
    FORMAT = "<h"

class Int16BE(Integer):
    FORMAT = ">h"

class Uint16LE(Integer):
    FORMAT = "<H"

class Uint16BE(Integer):
    FORMAT = ">H"

# 32 bits
class Int32LE(Integer):
    FORMAT = "<i"

class Int32BE(Integer):
    FORMAT = ">i"

class Uint32LE(Integer):
    FORMAT = "<I"

class Uint32BE(Integer):
    FORMAT = ">I"

