import ssl

class TLS:
    """ TLS implamentation using memory BIO """
    def __init__(self, writer, reader, certFile, privKey):
        """@param: writer and reader are asyncio stream writer and reader objects"""
        self._tlsInBuff = ssl.MemoryBIO()
        self._tlsOutBuff = ssl.MemoryBIO()
        ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        ctx.load_cert_chain(certFile, privKey)
        self._tlsObj = ctx.wrap_bio(self._tlsInBuff, self._tlsOutBuff, server_side=True)
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

        client_fin = await self.reader.read(4096)
        self._tlsInBuff.write(client_fin)
        self._tlsObj.do_handshake()

        server_fin = self._tlsOutBuff.read()
        self.writer.write(server_fin)
        await self.writer.drain()

    async def write_tls(self,data):
        self._tlsObj = write(data)
        _data = self._tlsOutBuff.read()
        _res = self.writer.write(_data)
        await self.writer.drain()
        return _res

    async def read_tls(self, size):
        _rData = await self.reader.read(size)
        self._tlsInBuff.write(_rData)
        data = self._tlsObj.read()
        return data
