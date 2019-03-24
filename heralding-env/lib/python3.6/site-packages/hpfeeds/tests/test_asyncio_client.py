import asyncio
import logging
import socket
import unittest

from hpfeeds.asyncio import ClientSession
from hpfeeds.broker import prometheus
from hpfeeds.broker.auth.memory import Authenticator
from hpfeeds.broker.server import Server


class TestAsyncioClientIntegration(unittest.TestCase):

    log = logging.getLogger('hpfeeds.test_asyncio_client')

    def setUp(self):
        prometheus.reset()

        assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_client_connections') == 0

        self.sock = sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', 0))
        self.port = sock.getsockname()[1]

        authenticator = Authenticator({
            'test': {
                'secret': 'secret',
                'subchans': ['test-chan'],
                'pubchans': ['test-chan'],
                'owner': 'some-owner',
            }
        })

        self.server = Server(authenticator, sock=self.sock)

    def test_subscribe_and_publish(self):
        async def inner():
            self.log.debug('Starting server')
            server_future = asyncio.ensure_future(self.server.serve_forever())

            self.log.debug('Creating client service')
            client = ClientSession('127.0.0.1', self.port, 'test', 'secret')
            client.subscribe('test-chan')

            # Wait till client connected
            await client.when_connected

            assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_client_connections') == 1
            assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_connection_made') == 1

            self.log.debug('Publishing test message')
            client.publish('test-chan', b'test message')

            self.log.debug('Waiting for read()')
            assert ('test', 'test-chan', b'test message') == await client.read()

            # We would test this after call to subscribe, but need to wait until sure server has processed command
            assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_subscriptions', {'ident': 'test', 'chan': 'test-chan'}) == 1

            # This will only have incremented when server has processed auth message
            # Test can only reliably assert this is the case after reading a message
            assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_connection_ready', {'ident': 'test'}) == 1

            self.log.debug('Stopping client')
            await client.close()

            assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_connection_send_buffer_fill', {'ident': 'test'}) == 12
            assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_connection_send_buffer_drain', {'ident': 'test'}) == 32

            self.log.debug('Stopping server')
            server_future.cancel()
            await server_future

        asyncio.get_event_loop().run_until_complete(inner())
        assert len(self.server.connections) == 0, 'Connection left dangling'
        assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_client_connections') == 0
        assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_connection_lost', {'ident': 'test'}) == 1

        # Closing should auto unsubscribe
        assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_subscriptions', {'ident': 'test', 'chan': 'test-chan'}) == 0

    def test_late_subscribe_and_publish(self):
        async def inner():
            self.log.debug('Starting server')
            server_future = asyncio.ensure_future(self.server.serve_forever())

            self.log.debug('Creating client service')
            client = ClientSession('127.0.0.1', self.port, 'test', 'secret')

            # Wait till client connected
            await client.when_connected

            assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_client_connections') == 1
            assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_connection_made') == 1

            # Subscribe to a new thing after connection is up
            client.subscribe('test-chan')

            self.log.debug('Publishing test message')
            client.publish('test-chan', b'test message')

            self.log.debug('Waiting for read()')
            assert ('test', 'test-chan', b'test message') == await client.read()

            # We would test this after call to subscribe, but need to wait until sure server has processed command
            assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_subscriptions', {'ident': 'test', 'chan': 'test-chan'}) == 1

            # Unsubscribe while the connection is up
            client.unsubscribe('test-chan')

            # FIXME: How to test that did anything!

            # This will only have incremented when server has processed auth message
            # Test can only reliably assert this is the case after reading a message
            assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_connection_ready', {'ident': 'test'}) == 1

            self.log.debug('Stopping client')
            await client.close()

            self.log.debug('Stopping server')
            server_future.cancel()
            await server_future

        asyncio.get_event_loop().run_until_complete(inner())
        assert len(self.server.connections) == 0, 'Connection left dangling'
        assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_client_connections') == 0
        assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_connection_lost', {'ident': 'test'}) == 1

        # Again, we should test this directly after calling unsubscribe(), but no ability to wait
        assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_subscriptions', {'ident': 'test', 'chan': 'test-chan'}) == 0

    def test_late_subscribe_and_publish_async_with(self):
        async def inner():
            self.log.debug('Starting server')
            server_future = asyncio.ensure_future(self.server.serve_forever())

            self.log.debug('Creating client service')
            async with ClientSession('127.0.0.1', self.port, 'test', 'secret') as client:
                assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_client_connections') == 1
                assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_connection_made') == 1

                # Subscribe to a new thing after connection is up
                client.subscribe('test-chan')

                self.log.debug('Publishing test message')
                client.publish('test-chan', b'test message')

                self.log.debug('Waiting for read()')
                assert ('test', 'test-chan', b'test message') == await client.read()

                # We would test this after call to subscribe, but need to wait until sure server has processed command
                assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_subscriptions', {'ident': 'test', 'chan': 'test-chan'}) == 1

                # Unsubscribe while the connection is up
                client.unsubscribe('test-chan')

                # FIXME: How to test that did anything!

                # This will only have incremented when server has processed auth message
                # Test can only reliably assert this is the case after reading a message
                assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_connection_ready', {'ident': 'test'}) == 1

            self.log.debug('Stopping server')
            server_future.cancel()
            await server_future

        asyncio.get_event_loop().run_until_complete(inner())
        assert len(self.server.connections) == 0, 'Connection left dangling'
        assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_client_connections') == 0
        assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_connection_lost', {'ident': 'test'}) == 1

        # Again, we should test this directly after calling unsubscribe(), but no ability to wait
        assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_subscriptions', {'ident': 'test', 'chan': 'test-chan'}) == 0

    def test_late_subscribe_and_publish_async_for(self):
        async def inner():
            server_future = asyncio.ensure_future(self.server.serve_forever())

            async with ClientSession('127.0.0.1', self.port, 'test', 'secret') as client:
                client.subscribe('test-chan')

                client.publish('test-chan', b'test message')

                async for ident, chan, payload in client:
                    assert ident == 'test'
                    assert chan == 'test-chan'
                    assert payload == b'test message'
                    break

            server_future.cancel()
            await server_future

        asyncio.get_event_loop().run_until_complete(inner())
        assert len(self.server.connections) == 0, 'Connection left dangling'

    def test_late_subscribe_and_publish_for_async_iter(self):
        async def inner():
            server_future = asyncio.ensure_future(self.server.serve_forever())

            async def example_iter():
                yield b'test message'

            async with ClientSession('127.0.0.1', self.port, 'test', 'secret') as client:
                client.subscribe('test-chan')

                await client.publish_async_iterable('test-chan', example_iter())

                assert ('test', 'test-chan', b'test message') == await client.read()

            server_future.cancel()
            await server_future

        asyncio.get_event_loop().run_until_complete(inner())
        assert len(self.server.connections) == 0, 'Connection left dangling'


class TestAsyncioClientIntegrationSSL(unittest.TestCase):

    log = logging.getLogger('hpfeeds.test_asyncio_client')

    def setUp(self):
        prometheus.reset()

        assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_client_connections') == 0

        import ssl
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain('hpfeeds/tests/testcert.crt', 'hpfeeds/tests/testcert.key')

        self.sock = sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', 0))
        self.port = sock.getsockname()[1]

        authenticator = Authenticator({
            'test': {
                'secret': 'secret',
                'subchans': ['test-chan'],
                'pubchans': ['test-chan'],
                'owner': 'some-owner',
            }
        })

        self.server = Server(authenticator, sock=self.sock, ssl=ssl_context)

    def test_subscribe_and_publish(self):
        async def inner():
            self.log.debug('Starting server')
            server_future = asyncio.ensure_future(self.server.serve_forever())

            assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_connection_send_buffer_fill', {'ident': 'test'}) is None
            assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_connection_send_buffer_drain', {'ident': 'test'}) is None

            import ssl
            ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile='hpfeeds/tests/testcert.crt')
            ssl_context.check_hostname = False

            self.log.debug('Creating client service')
            client = ClientSession('127.0.0.1', self.port, 'test', 'secret', ssl=ssl_context)
            client.subscribe('test-chan')

            # Wait till client connected
            await client.when_connected

            assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_client_connections') == 1
            assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_connection_made') == 1

            self.log.debug('Publishing test message')
            client.publish('test-chan', b'test message')

            self.log.debug('Waiting for read()')
            assert ('test', 'test-chan', b'test message') == await client.read()

            # We would test this after call to subscribe, but need to wait until sure server has processed command
            assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_subscriptions', {'ident': 'test', 'chan': 'test-chan'}) == 1

            # This will only have incremented when server has processed auth message
            # Test can only reliably assert this is the case after reading a message
            assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_connection_ready', {'ident': 'test'}) == 1

            self.log.debug('Stopping client')
            await client.close()

            assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_connection_send_buffer_fill', {'ident': 'test'}) == 12
            assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_connection_send_buffer_drain', {'ident': 'test'}) == 32

            self.log.debug('Stopping server')
            server_future.cancel()
            await server_future

        asyncio.get_event_loop().run_until_complete(inner())
        assert len(self.server.connections) == 0, 'Connection left dangling'
        assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_client_connections') == 0
        assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_connection_lost', {'ident': 'test'}) == 1

        # Closing should auto unsubscribe
        assert prometheus.REGISTRY.get_sample_value('hpfeeds_broker_subscriptions', {'ident': 'test', 'chan': 'test-chan'}) == 0
