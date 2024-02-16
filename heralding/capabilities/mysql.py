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

import os
import struct
import logging

from heralding.capabilities.handlerbase import HandlerBase

logger = logging.getLogger(__name__)


# Implemented according to https://dev.mysql.com/doc/internals/en/connection-phase-packets.html
class MySQL(HandlerBase):

  def __init__(self, options):
    super().__init__(options)
    self.PROTO_VER = b'\x0a'
    self.SERVER_VER = b'5.7.16\x00'
    self.AUTH_PLUGIN = b'mysql_native_password\x00'  # SHA-1 hash of password

  @staticmethod
  def convert4To3Byte(num):
    # MySQL protocol requires 3 byte integers for payload length
    return struct.pack("<I", num)[:3]

  def server_greeting(self):
    # Server Greeting(HandshakeV10) Packet:

    # 0x00 0x03    Payload length
    # 0x03 0x01    Sequence No
    # 0x04 0x01    Protocol version (0x0A)
    # 0x05 0x07    MySQL version (5.7.16\0 in this case, variable length in general)
    # 0x0C 0x04    Thread ID
    # 0x10 0x09    Salt (8 random bytes + \0)
    # 0x19 0x02    Server capabilities (0xFF 0x7F)
    # 0x1B 0x01    Server language (0x21 = utf8 COLLATE utf8_general_ci)
    # 0x1C 0x02    Server status (0x02 0x00)
    # 0x1E 0x02    Extended server capabilities (0xFF 0x81)
    # 0x20 0x01    Authentication plugin length
    # 0x21 0x0A    Unused (zeros)
    # 0x2B 0x0D    Salt (12 random bytes + \0)
    # 0x38 0x16    Authentication plugin ('mysql_native_password\0')

    # NB: actual payload without the first four bytes (Payload lenght + sequence no)

    # packet_length including payload_length+sequence_no
    packet_length = 0x3+0x1+0x1+len(self.SERVER_VER)+0x04+(0x08+0x01)+0x02+0x01 + \
        0x02+0x02+0x01+0x0A+0x0D+len(self.AUTH_PLUGIN)

    payload_len = MySQL.convert4To3Byte(packet_length - 0x04)
    seq_no = b'\x00'  # Always will be first packet
    thread_id = struct.pack("<I", 4321)
    salt_1 = os.urandom(8) + b'\x00'
    server_cap = b'\xFF\xF7'
    server_lang = b'\x21'
    server_status = b'\x02\x00'
    ext_server_cap = b'\xFF\x81'
    auth_plugin_len = bytes([len(self.AUTH_PLUGIN) - 1])
    zeros = bytes(0x0A)
    salt_2 = os.urandom(12) + b'\x00'

    packet = payload_len+seq_no+self.PROTO_VER+self.SERVER_VER+thread_id +\
        salt_1+server_cap+server_lang+server_status+ext_server_cap+auth_plugin_len +\
        zeros+salt_2+self.AUTH_PLUGIN

    return packet

  def auth_switch_request(self, seq_no):
    # Auth Switch Request Packet:

    # 0x00 0x03    Payload length
    # 0x03 0x01    Sequence No
    # 0x04 0x01    Auth switch request (0xFE)
    # 0x05 0x16    Auth method name (variable length, NUL-terminated)
    # 0x1B 0x15    Auth method data (20 bytes of random salt + \0)

    # Incase any client using other auth methods, request client to switch to 'mysql_native_password'

    packet_length = 3 + 1 + 1 + len(self.AUTH_PLUGIN) + 20 + 1
    payload_len = MySQL.convert4To3Byte(packet_length - 4)
    seq_no = bytes([seq_no])
    auth_switch_req = b'\xFE'
    auth_data = os.urandom(20) + b'\x00'

    packet = payload_len + seq_no + auth_switch_req + self.AUTH_PLUGIN + auth_data

    return packet

  def auth_failed(self, seq_no, user, server, using_password):
    # Auth Failed Packet(Error 1045):

    # 0x00 0x03    Payload length
    # 0x03 0x01    Sequence #
    # 0x04 0x01    Error packet (0xFF)
    # 0x05 0x02    Error code (1045, 0x0415)
    # 0x07 0x06    SQL State (#28000)
    # 0x0D  ??     Error message

    error_msg = bytes(
        "Access denied for user '{}'@'{}' (using password: {})".format(
            user, server, using_password), 'utf-8')
    full_length = 3 + 1 + 1 + 2 + 6 + len(error_msg)  # taking out null

    payload_len = MySQL.convert4To3Byte(full_length - 4)
    seq_no = bytes([seq_no])
    error_packet = b'\xFF'  # Error Packet ID
    error_code = b'\x15\x04'  # Error code 1045 (0x0415)
    sql_state = bytes("#28000", 'utf-8')

    packet = payload_len + seq_no + error_packet + error_code + sql_state + error_msg
    return packet

  async def execute_capability(self, reader, writer, session):
    try:
      await self._handle_session(reader, writer, session)
    except struct.error as exc:
      logger.debug('MySQL connection error: %s', exc)
      session.end_session()

  async def _handle_session(self, reader, writer, session):
    # HandshakeResponse41 Packet:

    # 0x00 0x03    Payload length
    # 0x03 0x01    Sequence No
    # 0x04 0x04    Client capability flags
    # 0x08 0x04    Max packet size
    # 0x0C 0x01    Client character set
    # 0x0D 0x17    Unused(zeros)
    # 0x24 ??      User name (NUL-terminated)
    # XX   0x01    Password length
    # XX+1 ??      Password
    # YY   ??      Schema (NUL-terminated)
    # ZZ   ??      Client authentication plugin (NUL-terminated)
    # RR   ??      Client connection attibutes

    address = writer.get_extra_info('peername')[0]
    writer.write(self.server_greeting())
    await writer.drain()
    data = await reader.read(2048)

    # Handle empty data and quit command
    if not data:
      logger.warning("Got no response from client. Ending the session")
      session.end_session()
      return
    elif data == b'\x01\x00\x00\x00\x01':
      logger.warning("Received COM_QUIT from client. Ending the session")
      session.end_session()
      return

    caps = int.from_bytes(data[0x04:0x08], byteorder='little')

    # Check if client version is above 4.1 , if not terminate session
    if not caps & 0x00000200:
      logger.warning(
          "Client vesrion should be 4.1 or above. Ending the session")
      session.end_session()
      return

    try:
      max_size = int.from_bytes(data[0x08:0x0C], byteorder='little')
      username_end_pos = data.index(b'\x00', 0x24, max_size - 0x24)
      username = str(data[0x24:username_end_pos], 'utf-8')
      password_len = data[username_end_pos + 1]
      using_password = "YES" if password_len > 0 else "NO"
      plugin_offset = username_end_pos + 1 + 1  # start offset of auth_plugin
      seq_no = 2  # if no auth_switch_request
      password_enc = ''

      if password_len > 0:
        # for logging coverted to printable hex
        password_enc = data[plugin_offset:plugin_offset + password_len].hex()
        plugin_offset = plugin_offset + password_len
    except ValueError:
      logger.warning("Malformed packet received. Ending the session")
      session.end_session()
      return

    # check if schema(db) is present
    if caps & 0x00000008:
      schema_offset = plugin_offset  # start offset of db
      try:
        schema_end_pos = data.index(b'\x00', schema_offset,
                                    max_size - schema_offset)
        plugin_offset = schema_end_pos + 1
      except ValueError:
        logger.warning("Could not find the schema. Ending the session")
        session.end_session()
        return

    # check if plugin_auth enabled
    if caps & 0x00080000:
      try:
        plugin_auth_offset = plugin_offset
        plugin_auth_pos = data.index(b'\x00', plugin_auth_offset,
                                     max_size - plugin_auth_offset)
        plugin_auth = data[plugin_auth_offset:plugin_auth_pos]
      except ValueError:
        logger.warning(
            "Cloud not find the plugin_auth data. Ending the session")
        session.end_session()
        return

      if "mysql_native_password" != str(plugin_auth, 'utf-8'):
        writer.write(self.auth_switch_request(seq_no))
        await writer.drain()
        if (await reader.read(1024)):
          seq_no = 4

    session.add_auth_attempt(
        'encrypted', username=username, password=password_enc)
    writer.write(self.auth_failed(seq_no, username, address, using_password))
    await writer.drain()
