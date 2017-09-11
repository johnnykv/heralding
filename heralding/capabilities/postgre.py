import struct
import logging

from heralding.capabilities.handlerbase import HandlerBase

logger = logging.getLogger(__name__)


class Postgre(HandlerBase):
    async def execute_capability(self, reader, writer, session):
        await self._handle_session(session, reader, writer)

    async def _handle_session(self, session, reader, writer):
        # Read (we blindly assume) SSL request and deny it
        await self.read_msg(reader, writer)
        writer.write('N'.encode('ascii'))

        session.activity()

        # Read login details
        data = await self.read_msg(reader, writer)
        login_dict = self.parse_dict(data)

        # Request plain text password login
        password_request = ['R'.encode('ascii'), 8, 3]
        writer.write(struct.pack('>c I I', *password_request))
        await writer.drain()

        # Read password
        data = await self.read_msg(reader, writer)
        password = self.parse_str(data)
        username = login_dict['user']
        session.add_auth_attempt('plaintext', username=username, password=password)

        # Report login failure
        writer.write('E'.encode('ascii'))
        fail = [
            'SFATAL'.encode('ascii'),
            b'\x00',
            'C28P01'.encode('ascii'),
            b'\x00',
            'Mpassword authentication failed for user "{}"'.format(username).encode('utf-8'),
            b'\x00',
            'Fauth.c'.encode('ascii'),
            b'\x00',
            'L288'.encode('ascii'),
            b'\x00',
            'Rauth_failed'.encode('ascii'),
            b'\x00',
            b'\x00',
        ]
        length = 0
        for f in fail:
            length += len(f)
        writer.write(struct.pack('>I', length+4))
        for f in fail:
            writer.write(f)

        await writer.drain()

        session.end_session()

    async def read_msg(self, reader, writer):
        i = await reader.read(4)
        length = struct.unpack('>I', i)[0]
        data = await reader.read(length)
        return data

    def parse_dict(self, data):
        dct = {}
        mode = 'pad'
        key = []
        value = []

        for c in struct.iter_unpack('c', data):
            c = c[0]

            if mode == 'pad':
                if c in (bytes([0]), bytes([3])):
                    continue
                else:
                    mode = 'key'

            if mode == 'key':
                if c == bytes([0]):
                    mode = 'value'
                else:
                    key.append(c.decode())

            elif mode == 'value':
                if c == bytes([0]):
                    dct[''.join(key)] = ''.join(value)
                    key = []
                    value = []
                    mode = 'pad'
                else:
                    value.append(c.decode())

        return dct

    def parse_str(self, data):
        data_array = bytearray(data)
        return data_array[1:-1].decode('utf-8')
