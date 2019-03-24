import sys

from twisted.application.internet import ClientService
from twisted.application.service import MultiService
from twisted.internet import defer
from twisted.internet.endpoints import clientFromString

from .factory import ClientFactory
from .protocol import ClientProtocol


class _Protocol(ClientProtocol):

    '''
    An implementation of the HPFeeds Twisted Client Protocol that is used
    by ClientService.
    '''

    def connectionMade(self):
        if hasattr(self.transport, 'setTcpKeepAlive'):
            self.transport.setTcpKeepAlive(10)

    def connectionReady(self):
        '''
        Called when a connection has been established and authentication has
        completed.

        Subscribe to any requested channels.
        '''
        self.factory.service.protocol = self

        for topic in self.factory.service.subscriptions:
            self.subscribe(self.factory.service.ident, topic)

        # We are connected and ready for business
        self.factory.service.whenConnected.callback(None)

    def connectionLost(self, reason):
        self.factory.service.protocol = None
        self.factory.service.whenConnected = defer.Deferred()
        self.factory = None

    def onPublish(self, ident, chan, data):
        '''
        Called by messageReceived when an OP_PUBLISH has been parsed.

        All received messages are pushed into owning services read_queue (a
        DeferredQueue).
        '''
        self.factory.service.read_queue.put((ident, chan, data))


class ClientSessionService(MultiService):

    '''
    A service that maintains a connection to a hpfeeds broker and provides
    helpers for reading and writing to the broker.
    '''

    def __init__(self, endpoint, ident, secret, retryPolicy=None):
        super(ClientSessionService, self).__init__()

        self.ident = ident

        self.read_queue = defer.DeferredQueue()
        self.subscriptions = set()
        self.protocol = None

        from twisted.internet import reactor

        if isinstance(endpoint, str):
            self.client_endpoint = clientFromString(reactor, endpoint)
        elif hasattr(endpoint, 'connect'):
            self.client_endpoint = endpoint
        else:
            raise ValueError('endpoint must be a str or implement IStreamClientEndpoint')

        self.client_factory = ClientFactory.forProtocol(_Protocol, ident, secret)
        self.client_factory.service = self

        self.client_service = ClientService(
            self.client_endpoint,
            self.client_factory,
            retryPolicy=retryPolicy,
        )
        self.client_service.setServiceParent(self)

        self.whenConnected = defer.Deferred()

    def publish(self, chan, payload):
        if self.protocol:
            self.protocol.publish(self.ident, chan, payload)

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
        Returns a Deferred which fires with the next available message received
        from the broker.

        If a message has already been received and is queue the deferred will
        fire immediately.
        '''
        return self.read_queue.get()

    def __enter__(self):
        raise TypeError("Use async with instead")

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    if sys.version_info[0] > 2:
        import asyncio

        @asyncio.coroutine
        @defer.inlineCallbacks
        def __aenter__(self):
            self.startService()
            yield self.whenConnected
            defer.returnValue(self)

        @asyncio.coroutine
        @defer.inlineCallbacks
        def __aexit__(self, exc_type, exc_val, exc_tb):
            yield self.stopService()

        @asyncio.coroutine
        @defer.inlineCallbacks
        def __aiter__(self):
            defer.returnValue(self)

        @asyncio.coroutine
        @defer.inlineCallbacks
        def __anext__(self):
            if not self.running:
                raise StopAsyncIteration()
            message = yield self.read()
            defer.returnValue(message)
