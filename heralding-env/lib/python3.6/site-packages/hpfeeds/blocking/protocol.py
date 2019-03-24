from __future__ import absolute_import

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
    readauth,
    readerror,
    readinfo,
    readpublish,
    readsubscribe,
    readunsubscribe,
)


class BaseProtocol(object):

    def __init__(self):
        self.unpacker = Unpacker()

    def connection_made(self):
        pass

    def connection_lost(self, reason):
        pass

    def protocol_error(self, reason):
        pass

    def on_error(self, error):
        raise NotImplementedError(self.on_info)

    def on_info(self, name, rand):
        raise NotImplementedError(self.on_info)

    def on_auth(self, ident, hash):
        raise NotImplementedError(self.on_auth)

    def on_publish(self, ident, chan, data):
        raise NotImplementedError(self.on_publish)

    def on_subscribe(self, ident, channel):
        raise NotImplementedError(self.on_subscribe)

    def on_unsubscribe(self, ident, channel):
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

    def data_received(self, data):
        self.unpacker.feed(data)
        try:
            for opcode, data in self.unpacker:
                self.message_received(opcode, data)
        except ProtocolException as e:
            self.protocol_error(str(e))
            self.transport.close()


class ClientProtocol(BaseProtocol):

    def __init__(self, ident, secret):
        self.ident = ident
        self.secret = secret
        super(ClientProtocol, self).__init__()

    def connection_ready(self):
        ''' Called when a client has connected to broker and sent authentication '''
        pass

    def on_info(self, name, rand):
        self.transport.write(msgauth(rand, self.ident, self.secret))
        self.connection_ready()

    def on_auth(self, ident, hash):
        self.protocol_error('Unexpected OP_AUTH')
        self.transport.close()

    def on_subscribe(self, ident, channel):
        self.protocol_error('Unexpected OP_SUBSCRIBE')
        self.transport.close()

    def on_unsubscribe(self, ident, channel):
        self.protocol_error('Unexpected OP_UNSUBSCRIBE')
        self.transport.close()
