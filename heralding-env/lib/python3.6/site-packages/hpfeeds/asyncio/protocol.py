import asyncio

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


class BaseProtocol(asyncio.Protocol):

    def __init__(self):
        self.unpacker = Unpacker()

    def protocol_error(self, reason):
        '''
        Called when an unrecoverable protocol error has been detected. The
        connection will be dropped.
        '''
        pass

    def on_error(self, error):
        '''
        Called by message_received when an OP_ERROR has been parsed.
        '''
        raise NotImplementedError(self.on_error)

    def on_info(self, name, rand):
        '''
        Called by message_received when an OP_INFO has been parsed.
        '''
        raise NotImplementedError(self.on_info)

    def on_auth(self, ident, secret):
        '''
        Called by message_received when an OP_AUTH has been parsed.
        '''
        raise NotImplementedError(self.on_auth)

    def on_publish(self, ident, chan, data):
        '''
        Called by message_received when an OP_PUBLISH has been parsed.
        '''
        raise NotImplementedError(self.on_publish)

    def on_subscribe(self, ident, chan):
        '''
        Called by message_received when an OP_SUBSCRIBE has been parsed.
        '''
        raise NotImplementedError(self.on_subscribe)

    def on_unsubscribe(self, ident, chan):
        '''
        Called by message_received when an OP_UNSUBSCRIBE has been parsed.
        '''
        raise NotImplementedError(self.on_unsubscribe)

    def message_received(self, opcode, data):
        if opcode == OP_ERROR:
            return self.on_error(readerror(data))
        elif opcode == OP_INFO:
            return self.on_info(*readinfo(data))
        elif opcode == OP_AUTH:
            return self.on_auth(*readauth(data))
        elif opcode == OP_PUBLISH:
            return self.on_publish(*readpublish(data))
        elif opcode == OP_SUBSCRIBE:
            return self.on_subscribe(*readsubscribe(data))
        elif opcode == OP_UNSUBSCRIBE:
            return self.on_unsubscribe(*readunsubscribe(data))

        # Can't recover from an unknown opcode, so drop connection
        self.protocol_error('Unknown message opcode: {!r}'.format(opcode))
        self.transport.close()

    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data):
        self.unpacker.feed(data)
        try:
            for opcode, data in self.unpacker:
                self.message_received(opcode, data)
        except ProtocolException as e:
            # Can't recover from a protocol decoding error, so drop connection
            self.protocol_error(str(e))
            self.transport.close()

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
    A base class for implementing hpfeeds client functionality in aio.
    '''

    def __init__(self, ident, secret):
        self.ident = ident
        self.secret = secret
        super().__init__()

    def connection_ready(self):
        '''
        Called when a connection has been established and authentication has
        completed.
        '''
        pass

    def on_info(self, name, rand):
        '''
        Called by message_received when an OP_INFO has been parsed.

        The default client implementation will send an appropriate OP_AUTH and
        call connection_ready.
        '''
        self.auth(rand, self.ident, self.secret)
        self.connection_ready()

    def on_auth(self, ident, secret):
        '''
        Called by message_received when an OP_AUTH has been parsed.

        A HPFeeds **client** should never receive an OP_AUTH. By default it will
        call protocol_error and drop the connection.
        '''
        self.protocol_error('Unexpected OP_AUTH')
        self.transport.close()

    def on_subscribe(self, ident, chan):
        '''
        Called by message_received when an OP_SUBSCRIBE has been parsed.

        A HPFeeds **client** should never receive an OP_SUBSCRIBE. By default
        it will call protocol_error and drop the connection.
        '''
        self.protocol_error('Unexpected OP_SUBSCRIBE')
        self.transport.close()

    def on_unsubscribe(self, ident, chan):
        '''
        Called by message_received when an OP_UNSUBSCRIBE has been parsed.

        A HPFeeds **client** should never receive an OP_UNSUBSCRIBE. By default
        it will call protocol_error and drop the connection.
        '''
        self.protocol_error('Unexpected OP_UNSUBSCRIBE')
        self.transport.close()

    def error(self, error):
        raise RuntimeError('Client tried to set OP_ERROR to server, this is a protocol violation')

    def info(self, name, rand):
        raise RuntimeError('Client tried to set OP_INFO to server, this is a protocol violation')
