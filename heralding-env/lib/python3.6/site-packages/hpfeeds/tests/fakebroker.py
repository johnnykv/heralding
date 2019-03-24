'''
This module implements an incredibly basic broker.

In has no authentication and no channels.

It is meant to support py 2 and py 3.
'''

import socket
import sys

from twisted.internet.protocol import Factory

from hpfeeds.twisted import BaseProtocol


class FakeBrokerProtocol(BaseProtocol):

    def connectionMade(self):
        self.info('hpfeeds', b'\x00' * 8)
        self.factory.broker.connections.add(self)

    def connectionLost(self, reason):
        self.factory.broker.connections.discard(self)

    def onAuth(self, ident, chan):
        pass

    def onSubscribe(self, ident, chan):
        pass

    def onUnsubscribe(self, ident, chan):
        pass

    def onPublish(self, ident, chan, payload):
        for con in list(self.factory.broker.connections):
            con.publish(ident, chan, payload)


class FakeBroker(object):

    def __init__(self):
        self.connections = set()

        self.sock = sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        sock.bind(('127.0.0.1', 0))
        sock.listen(100)

        self.port = sock.getsockname()[1]

    def start(self):
        factory = Factory.forProtocol(FakeBrokerProtocol)
        factory.broker = self

        from twisted.internet import reactor
        self.adopted_port = reactor.adoptStreamPort(self.sock.fileno(), socket.AF_INET, factory)
        print('Port adopted', self.port)

    def close(self):
        return self.adopted_port.stopListening()


def setup_default_reactor(test):
    if 'twisted.internet.reactor' in sys.modules:
        del sys.modules['twisted.internet.reactor']

    from twisted.internet import selectreactor
    selectreactor.install()

    from twisted.internet import reactor
    return reactor


def setup_asyncio_reactor(test):
    import asyncio
    from twisted.internet import asyncioreactor

    _old_loop = asyncio.get_event_loop()

    if 'twisted.internet.reactor' in sys.modules:
        del sys.modules['twisted.internet.reactor']

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    asyncioreactor.install(eventloop=loop)

    def cleanup():
        asyncio.get_event_loop().close()
        asyncio.set_event_loop(_old_loop)

    test.addCleanup(cleanup)

    from twisted.internet import reactor
    return reactor
