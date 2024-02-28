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

import ssl
import logging

logger = logging.getLogger(__name__)


class TLSHandshakeError(Exception):

  def __init__(self, message=""):
    Exception.__init__(self, message)


class TLS:
  """ TLS implamentation using memory BIO """

  def __init__(self, writer, reader, pem_file):
    """@param: writer and reader are asyncio stream writer and reader objects"""
    self._tlsInBuff = ssl.MemoryBIO()
    self._tlsOutBuff = ssl.MemoryBIO()
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1_1)
    ctx.set_ciphers('RSA:!aNULL')
    ctx.check_hostname = False
    ctx.load_cert_chain(pem_file)
    self._tlsObj = ctx.wrap_bio(
        self._tlsInBuff, self._tlsOutBuff, server_side=True)
    self.writer = writer
    self.reader = reader

  async def do_tls_handshake(self):
    client_hello = await self.reader.read(4096)
    self._tlsInBuff.write(client_hello)
    try:
      self._tlsObj.do_handshake()
    except ssl.SSLWantReadError:
      server_hello = self._tlsOutBuff.read()
      self.writer.write(server_hello)
      await self.writer.drain()
    except ssl.SSLError as e:
      if "WRONG_VERSION_NUMBER" in e.args[1]:
        logger.debug("Client tried to connect with wrong SSL version")
      else:
        logger.debug(e.args[1])

    client_fin = await self.reader.read(4096)
    self._tlsInBuff.write(client_fin)
    try:
      self._tlsObj.do_handshake()
    except ssl.SSLWantReadError:
      raise TLSHandshakeError("Expected more data in Clinet FIN")

    server_fin = self._tlsOutBuff.read()
    self.writer.write(server_fin)
    await self.writer.drain()

  async def write_tls(self, data):
    self._tlsObj.write(data)
    _data = self._tlsOutBuff.read()
    _res = self.writer.write(_data)
    await self.writer.drain()
    return _res

  async def read_tls(self, size):
    data = b""
    # Check if we have any leftover data in the buffer
    try:
      data += self._tlsObj.read(size)
    except ssl.SSLWantReadError:
      pass

    # iterate until we have all needed plaintext
    while len(data) < size:
      if self.reader.at_eof():
        break
      try:
        # read ciphertext
        _rData = await self.reader.read(1)
        # put ciphertext into SSL machine
        self._tlsInBuff.write(_rData)
        # try to fill plaintext buffer
        data += self._tlsObj.read(size)
      except ssl.SSLWantReadError:
        pass

    return data
