from twisted.internet.protocol import Protocol
from twisted.python import log

from hpfeeds.exceptions import ProtocolException
from hpfeeds.protocol import (
    OP_AUTH,
    OP_ERROR,
    OP_INFO,
    OP_PUBLISH,
    OP_SUBSCRIBE,
    OP_UNSUBSCRIBE,
    Unpacker,
    msgauth,
    msgerror,
    msginfo,
    msgpublish,
    msgsubscribe,
    msgunsubscribe,
    readauth,
    readerror,
    readinfo,
    readpublish,
    readsubscribe,
    readunsubscribe,
)


class BaseProtocol(Protocol):

    def __init__(self):
        self.unpacker = Unpacker()

    def protocolError(self, reason):
        '''
        Called when an unrecoverable protocol error has been detected. The
        connection will be dropped.
        '''
        log.err(reason)

    def onError(self, error):
        '''
        Called by messageReceived when an OP_ERROR has been parsed.
        '''
        raise NotImplementedError(self.onError)

    def onInfo(self, name, rand):
        '''
        Called by messageReceived when an OP_INFO has been parsed.
        '''
        raise NotImplementedError(self.onInfo)

    def onAuth(self, ident, secret):
        '''
        Called by messageReceived when an OP_AUTH has been parsed.
        '''
        raise NotImplementedError(self.onAuth)

    def onPublish(self, ident, chan, data):
        '''
        Called by messageReceived when an OP_PUBLISH has been parsed.
        '''
        raise NotImplementedError(self.onPublish)

    def onSubscribe(self, ident, chan):
        '''
        Called by messageReceived when an OP_SUBSCRIBE has been parsed.
        '''
        raise NotImplementedError(self.onSubscribe)

    def onUnsubscribe(self, ident, chan):
        '''
        Called by messageReceived when an OP_UNSUBSCRIBE has been parsed.
        '''
        raise NotImplementedError(self.onUnsubscribe)

    def messageReceived(self, opcode, data):
        if opcode == OP_ERROR:
            return self.onError(readerror(data))
        elif opcode == OP_INFO:
            return self.onInfo(*readinfo(data))
        elif opcode == OP_AUTH:
            return self.onAuth(*readauth(data))
        elif opcode == OP_PUBLISH:
            return self.onPublish(*readpublish(data))
        elif opcode == OP_SUBSCRIBE:
            return self.onSubscribe(*readsubscribe(data))
        elif opcode == OP_UNSUBSCRIBE:
            return self.onUnsubscribe(*readunsubscribe(data))

        # Can't recover from an unknown opcode, so drop connection
        self.protocolError('Unknown message opcode: {!r}'.format(opcode))
        self.transport.loseConnection()

    def dataReceived(self, data):
        self.unpacker.feed(data)
        try:
            for opcode, data in self.unpacker:
                self.messageReceived(opcode, data)
        except ProtocolException as e:
            # Can't recover from a protocol decoding error, so drop connection
            self.protocolError(str(e))
            self.transport.loseConnection()

    def error(self, error):
        self.transport.write(msgerror(error))

    def info(self, name, rand):
        self.transport.write(msginfo(name, rand))

    def auth(self, rand, ident, secret):
        self.transport.write(msgauth(rand, ident, secret))

    def publish(self, ident, channel, payload):
        self.transport.write(msgpublish(ident, channel, payload))

    def subscribe(self, ident, channel):
        self.transport.write(msgsubscribe(ident, channel))

    def unsubscribe(self, ident, channel):
        self.transport.write(msgunsubscribe(ident, channel))


class ClientProtocol(BaseProtocol):

    '''
    A base class for implementing hpfeeds client functionality in Twisted.
    '''

    def connectionReady(self):
        '''
        Called when a connection has been established and authentication has
        completed.
        '''
        pass

    def onInfo(self, name, rand):
        '''
        Called by messageReceived when an OP_INFO has been parsed.

        The default client implementation will send an appropriate OP_AUTH and
        call connectionReady.
        '''
        self.auth(rand, self.factory.ident, self.factory.secret)
        self.connectionReady()

    def onAuth(self, ident, secret):
        '''
        Called by messageReceived when an OP_AUTH has been parsed.

        A HPFeeds **client** should never receive an OP_AUTH. By default it will
        call protocolError and drop the connection.
        '''
        self.protocolError('Unexpected OP_AUTH')
        self.transport.loseConnection()

    def onSubscribe(self, ident, chan):
        '''
        Called by messageReceived when an OP_SUBSCRIBE has been parsed.

        A HPFeeds **client** should never receive an OP_SUBSCRIBE. By default
        it will call protocolError and drop the connection.
        '''
        self.protocolError('Unexpected OP_SUBSCRIBE')
        self.transport.loseConnection()

    def onUnsubscribe(self, ident, chan):
        '''
        Called by messageReceived when an OP_UNSUBSCRIBE has been parsed.

        A HPFeeds **client** should never receive an OP_UNSUBSCRIBE. By default
        it will call protocolError and drop the connection.
        '''
        self.protocolError('Unexpected OP_UNSUBSCRIBE')
        self.transport.loseConnection()

    def error(self, error):
        raise RuntimeError('Client tried to set OP_ERROR to server, this is a protocol violation')

    def info(self, name, rand):
        raise RuntimeError('Client tried to set OP_INFO to server, this is a protocol violation')
