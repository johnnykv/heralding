# We need this in order to reduce the number of third-party modules.
# It is a part of code from socketserver, that adjusted to work with
# asyncio in our specific case.


class AsyncBaseRequestHandler:
    """Asynchronous analogue of socketserver.BaseRequestHandler."""
    def __init__(self, reader, writer, client_address):
        self.rfile = reader
        self.wfile = writer
        self.client_address = client_address

    async def run(self):
        self.setup()
        try:
            await self.handle()
        finally:
            self.finish()

    def setup(self):
        pass

    async def handle(self):
        pass

    def finish(self):
        pass
