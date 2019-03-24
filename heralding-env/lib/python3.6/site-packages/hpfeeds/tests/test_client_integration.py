import asyncio
import logging
import socket
import threading
import unittest

from hpfeeds import client
from hpfeeds.broker import prometheus
from hpfeeds.broker.auth.memory import Authenticator
from hpfeeds.broker.server import Server
from hpfeeds.protocol import readpublish


class TestClientIntegration(unittest.TestCase):

    log = logging.getLogger('hpfeeds.testserver')

    def _server_thread(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.server_future = loop.create_future()

        async def inner():
            authenticator = Authenticator({
                'test': {
                    'secret': 'secret',
                    'subchans': ['test-chan'],
                    'pubchans': ['test-chan'],
                    'owner': 'some-owner',
                }
            })

            self.server = Server(authenticator, sock=self.sock)

            self.log.debug('Starting server')
            future = asyncio.ensure_future(self.server.serve_forever())

            self.log.debug('Awaiting test teardown')
            await self.server_future

            self.log.debug('Stopping test server')
            future.cancel()
            await future

        loop.run_until_complete(inner())

    def setUp(self):
        prometheus.reset()

        assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_client_connections') == 0

        self.sock = sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', 0))
        self.port = sock.getsockname()[1]

        self.server_thread = threading.Thread(
            target=self._server_thread,
        )
        self.server_thread.start()

    def test_subscribe_and_publish(self):
        c = client.new('127.0.0.1', self.port, 'test', 'secret')

        c.subscribe('test-chan')
        c._subscribe()

        # If we have subscribed to a channel we should be able to see a
        # connection in monitoring
        assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_client_connections') == 1

        c.publish('test-chan', b'data')

        opcode, data = c._read_message()
        assert opcode == 3
        assert readpublish(data) == ('test', 'test-chan', b'data')

        # We managed to publish a message - check this is reflected in stats
        assert 1 == prometheus.REGISTRY.get_sample_value(
            'hpfeeds_broker_receive_publish_count',
            {'ident': 'test', 'chan': 'test-chan'}
        )

        # If we managed to read a message from the broker then we must be subscribed
        # Check this is reflected in stats
        assert 1 == prometheus.REGISTRY.get_sample_value(
            'hpfeeds_broker_subscriptions',
            {'ident': 'test', 'chan': 'test-chan'}
        )

        self.log.debug('Stopping client')
        c.stop()

        self.log.debug('Closing client')
        c.close()

    def tearDown(self):
        self.log.debug('Cancelling future')
        self.server_future.set_result(None)
        self.log.debug('Waiting')
        self.server_thread.join()

        assert len(self.server.connections) == 0, 'Connection left dangling'
        assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_client_connections') == 0

        assert 0 == prometheus.REGISTRY.get_sample_value(
            'hpfeeds_broker_subscriptions',
            {'ident': 'test', 'chan': 'test-chan'}
        )
