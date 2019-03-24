import asyncio
import logging
import socket
import sys

from .protocol import ClientProtocol


class _Protocol(ClientProtocol):

    '''
    An implementation of the HPFeeds AIO Client Protocol that is used
    by Client.
    '''

    def __init__(self, client):
        self.client = client
        super().__init__(client.ident, client.secret)

    def connection_made(self, transport):
        sock = transport.get_extra_info('socket')
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if sys.platform.startswith('linux'):
            sock.setsockopt(socket.SOL_TCP, socket.TCP_KEEPIDLE, 10)
            sock.setsockopt(socket.SOL_TCP, socket.TCP_KEEPINTVL, 5)
            sock.setsockopt(socket.SOL_TCP, socket.TCP_KEEPCNT, 3)
        super().connection_made(transport)

    def connection_ready(self):
        '''
        Called when a connection has been established and authentication has
        completed.

        Subscribe to any requested channels.
        '''
        self.client.protocol = self

        for topic in self.client.subscriptions:
            self.subscribe(self.ident, topic)

        # We are connected and ready for business
        self.client.when_connected.set_result(None)

    def connection_lost(self, reason):
        self.client.when_closed.set_result(None)

    def on_publish(self, ident, chan, data):
        '''
        Called by messageReceived when an OP_PUBLISH has been parsed.

        All received messages are pushed into owning services read_queue (a
        DeferredQueue).
        '''
        self.client.read_queue.put_nowait((ident, chan, data))


class ClientSession(object):

    '''
    A service that maintains a connection to a hpfeeds broker and provides
    helpers for reading and writing to the broker.
    '''

    log = logging.getLogger('hpfeeds.asyncio.client')

    def __init__(self, host, port, ident, secret, ssl=None):
        self.host = host
        self.port = port
        self.ident = ident
        self.secret = secret
        self.ssl = ssl

        self.read_queue = asyncio.Queue()
        self.subscriptions = set()
        self.protocol = None

        self.when_connected = asyncio.Future()
        self.closing = False
        self._ensure_connected = asyncio.ensure_future(self.reconnect())

    async def _tryconnect(self):
        while True:
            try:
                client = await asyncio.get_event_loop().create_connection(
                    lambda: _Protocol(self),
                    self.host,
                    self.port,
                    ssl=self.ssl,
                )
                return client
            except OSError as e:
                pass

            await asyncio.sleep(1)

    async def reconnect(self):
        while not self.closing:
            self.protocol = None
            self.when_closed = asyncio.Future()

            try:
                await self._tryconnect()
            except Exception as e:
                self. log.exception(e)

            await self.when_closed
            self.when_connected = asyncio.Future()

    def publish(self, chan, payload):
        if self.protocol:
            self.protocol.publish(self.ident, chan, payload)

    async def publish_async_iterable(self, channel, async_iterator):
        async for payload in async_iterator:
            self.publish(channel, payload)

    def subscribe(self, topic):
        if topic not in self.subscriptions:
            self.subscriptions.add(topic)
            if self.protocol:
                self.protocol.subscribe(self.ident, topic)

    def unsubscribe(self, topic):
        if topic in self.subscriptions:
            self.subscriptions.discard(topic)
            if self.protocol:
                self.protocol.unsubscribe(self.ident, topic)

    def read(self):
        '''
        Returns a future which fires with the next available message received
        from the broker.

        If a message has already been received and is queued the future will
        fire immediately.
        '''
        return self.read_queue.get()

    async def close(self):
        self.closing = True
        if self.protocol:
            self.protocol.transport.close()
        await self.when_closed

    def __enter__(self):
        raise TypeError("Use async with instead")

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    async def __aenter__(self):
        await self.when_connected
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.closing:
            raise StopAsyncIteration()
        message = await self.read()
        return message
