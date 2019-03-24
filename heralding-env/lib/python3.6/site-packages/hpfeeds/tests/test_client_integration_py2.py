import logging
import threading
import unittest

from hpfeeds import client
from hpfeeds.protocol import readpublish

from .fakebroker import FakeBroker, setup_default_reactor


class TestClientIntegration(unittest.TestCase):

    log = logging.getLogger('hpfeeds.testserver')

    def _server_thread(self):
        self.reactor = setup_default_reactor(self)
        self.server.start()
        self.reactor.run(installSignalHandlers=False)

    def setUp(self):
        self.server = FakeBroker()

        self.server_thread = threading.Thread(
            target=self._server_thread,
        )
        self.server_thread.start()

    def test_subscribe_and_publish(self):
        c = client.new('127.0.0.1', self.server.port, 'test', 'secret')

        c.subscribe('test-chan')
        c._subscribe()

        c.publish('test-chan', b'data')

        opcode, data = c._read_message()
        assert opcode == 3
        assert readpublish(data) == ('test', 'test-chan', b'data')

        self.log.debug('Stopping client')
        c.stop()

        self.log.debug('Closing client')
        c.close()

    def tearDown(self):
        self.log.debug('Cancelling future')
        self.server.close()
        self.reactor.callFromThread(self.reactor.stop)
        self.log.debug('Waiting')
        self.server_thread.join()

        assert len(self.server.connections) == 0, 'Connection left dangling'
