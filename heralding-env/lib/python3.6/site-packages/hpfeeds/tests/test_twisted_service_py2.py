from __future__ import print_function

import unittest

from twisted.internet import defer
from twisted.internet.endpoints import HostnameEndpoint

from hpfeeds.twisted import ClientSessionService

from .fakebroker import FakeBroker, setup_default_reactor


class TestClientIntegration(unittest.TestCase):

    def setUp(self):
        self.reactor = setup_default_reactor(self)

        self.server = FakeBroker()
        self.server.start()

    def test_subscribe_and_publish(self):
        @defer.inlineCallbacks
        def inner(reactor):
            print('Creating client service')
            endpoint = 'tcp:127.0.0.1:{}'.format(self.server.port)
            client = ClientSessionService(endpoint, 'test', 'secret')
            client.subscribe('test-chan')

            print('Starting client service')
            client.startService()

            # Wait till client connected
            print('Waiting to be connected')
            yield client.whenConnected

            print('Publishing test message')
            client.publish('test-chan', b'test message')

            print('Waiting for read()')
            payload = yield client.read()
            assert ('test', 'test-chan', b'test message') == payload

            print('Stopping client')
            yield client.stopService()

            print('Stopping server for reals')
            yield self.server.close()

        inner(self.reactor).addBoth(lambda *x: self.reactor.stop())
        self.reactor.run()

    def test_subscribe_and_publish_endpoint_impl(self):
        @defer.inlineCallbacks
        def inner(reactor):
            print('Creating client service')

            from twisted.internet import reactor
            endpoint = HostnameEndpoint(reactor, '127.0.0.1', self.server.port)

            client = ClientSessionService(endpoint, 'test', 'secret')
            client.subscribe('test-chan')

            print('Starting client service')
            client.startService()

            # Wait till client connected
            print('Waiting to be connected')
            yield client.whenConnected

            print('Publishing test message')
            client.publish('test-chan', b'test message')

            print('Waiting for read()')
            payload = yield client.read()
            assert ('test', 'test-chan', b'test message') == payload

            print('Stopping client')
            yield client.stopService()

            print('Stopping server for reals')
            yield self.server.close()

        inner(self.reactor).addBoth(lambda *x: self.reactor.stop())
        self.reactor.run()

    def test_subscribe_and_publish_endpoint_invalid(self):
        self.assertRaises(ValueError, ClientSessionService, 777, 'test', 'secret')
