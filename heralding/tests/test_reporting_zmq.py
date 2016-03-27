# Copyright (C) 2016 Johnny Vestergaard <jkv@unixcluster.dk>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import gevent
import gevent.event
import gevent.monkey
import gevent.queue

gevent.monkey.patch_all()

import unittest
import zmq.green as zmq
from zmq.utils import jsonapi

from heralding.reporting.zmq_logger import ZmqLogger, ZmqMessageTypes
from heralding.reporting.reporting_relay import ReportingRelay
import heralding.misc


class ZmqTests(unittest.TestCase):
    def setUp(self):
        self.test_running = True
        self.zmq_server_listning_event = gevent.event.Event()
        self.testing_queue = gevent.queue.Queue()
        self.reportingRelay = ReportingRelay()
        self.reportingRelay.start()

    def tearDown(self):
        self.test_running = False
        self.reportingRelay.stop()

    def test_connect(self):
        """Tests that we can connect and send data to a zmq puller"""

        # start dummy ZMQ server
        gevent.spawn(self._start_zmq_puller)
        self.zmq_server_listning_event.wait(5)

        # our local zmq logger
        zmq_url = 'tcp://localhost:{0}'.format(self.zmq_tcp_port)
        zmqLogger = ZmqLogger(zmq_url)
        zmqLogger.start()

        # inject some data into the logging relay singleton
        self.reportingRelay.queueLogData({'somekey': 'somedata'})

        # wait until the zmq server put something into the local testing queue
        received_data = self.testing_queue.get(5)
        received_data = received_data.split(' ', 1)
        topic, message = received_data[0], jsonapi.loads(received_data[1])

        self.assertEqual(topic, ZmqMessageTypes.HERALDING_AUTH_LOG.value)
        self.assertIn('somekey', message)
        self.assertEqual(message['somekey'], 'somedata')

    def _start_zmq_puller(self):
        context = heralding.misc.zmq_context

        socket = context.socket(zmq.PULL)
        self.zmq_tcp_port = socket.bind_to_random_port('tcp://*', min_port=40000, max_port=50000, max_tries=10)

        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)
        self.zmq_server_listning_event.set()
        while self.test_running:
            socks = dict(poller.poll(100))
            if socket in socks and socks[socket] == zmq.POLLIN:
                data = socket.recv()
                self.testing_queue.put(data)
        socket.close()
