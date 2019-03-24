import unittest

from hpfeeds.twisted import ClientFactory, ClientProtocol


class TestClientProtocol(unittest.TestCase):

    def test_instance_factory(self):
        factory = ClientFactory('ident', 'secret')
        assert factory.ident == 'ident'
        assert factory.secret == 'secret'

    def test_for_protocol(self):
        factory = ClientFactory.forProtocol(ClientProtocol, 'ident', 'secret')
        assert factory.ident == 'ident'
        assert factory.secret == 'secret'
