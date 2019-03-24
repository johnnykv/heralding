from twisted.internet.protocol import Factory

from .protocol import ClientProtocol


class ClientFactory(Factory):

    protocol = ClientProtocol

    def __init__(self, ident, secret):
        self.ident = ident
        self.secret = secret
