import asyncio
import socket
import unittest

import aiohttp

from hpfeeds.asyncio.client import ClientSession
from hpfeeds.broker import prometheus
from hpfeeds.broker.auth.memory import Authenticator
from hpfeeds.broker.server import Server


class TestBrokerPrometheusEndpoint(unittest.TestCase):

    def setUp(self):
        prometheus.reset()

        authenticator = Authenticator({
            'test': {
                'secret': 'secret',
                'subchans': ['test-chan'],
                'pubchans': ['test-chan'],
                'owner': 'some-owner',
            }
        })

        self.server = Server(authenticator, bind='127.0.0.1:20000', exporter='127.0.0.1:20001')

    def test_metrics_server(self):
        async def inner():
            server_future = asyncio.ensure_future(self.server.serve_forever())
            await self.server.when_started

            async with aiohttp.ClientSession() as session:
                async with session.get('http://127.0.0.1:20001/metrics') as resp:
                    metrics = await resp.text()
                    print(metrics)
                    assert 'hpfeeds_broker_client_connections 0.0' in metrics
                    assert 'hpfeeds_broker_connection_send_buffer_size{' not in metrics

            sock = socket.socket()
            sock.connect(('127.0.0.1', 20000))

            async with aiohttp.ClientSession() as session:
                async with session.get('http://127.0.0.1:20001/metrics') as resp:
                    metrics = await resp.text()
                    print(metrics)
                    assert 'hpfeeds_broker_client_connections 1.0' in metrics
                    assert 'hpfeeds_broker_connection_send_buffer_size{' not in metrics

            sock.close()

            async with ClientSession('127.0.0.1', 20000, 'test', 'secret'):
                async with aiohttp.ClientSession() as session:
                    async with session.get('http://127.0.0.1:20001/metrics') as resp:
                        metrics = await resp.text()
                        print(metrics)
                        assert 'hpfeeds_broker_client_connections 1.0' in metrics
                        assert 'hpfeeds_broker_connection_send_buffer_size{ident="test"} 0.0' in metrics

            server_future.cancel()
            await server_future

        asyncio.get_event_loop().run_until_complete(inner())
