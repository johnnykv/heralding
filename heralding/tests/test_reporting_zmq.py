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

import gevent.monkey
gevent.monkey.patch_all()

import unittest

import gevent
import gevent.event
import gevent.queue
import json
import pprint
import datetime

from zmq import green as zmq
from zmq.auth.thread import ThreadAuthenticator, AuthenticationThread
from zmq.utils import jsonapi

from heralding.reporting.zmq_logger import ZmqLogger, ZmqMessageTypes
from heralding.reporting.reporting_relay import ReportingRelay

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

        # start dummy ZMQ pull server
        gevent.spawn(self._start_zmq_puller)
        self.zmq_server_listning_event.wait(5)

        # our local zmq logger
        zmq_url = 'tcp://localhost:{0}'.format(self.zmq_tcp_port)
        client_public_key = "N[DC7+%FKdW3pJUPnaCwWxt-0/jo5Lrq&U28-GG}"
        client_secret_key = "Gwt%C0a8J/:9Jy$qpDNTy8wRzlnRD-HT8H>u7F{B"
        server_public_key = "^4b:-bZ8seRC+m2p(sg{7{skOuK*jInNeH^/Le}Q"
        zmqLogger = ZmqLogger(zmq_url, client_public_key, client_secret_key, server_public_key)
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
        context = zmq.Context()

        # Authenticator runs in different greenlet.
        auth = GreenThreadAuthenticator(context)
        auth.start()
        auth.allow('127.0.0.1')
        auth.configure_curve(domain='*', location='heralding/tests/zmq_public_keys')

        # Bind our mock zmq pull server
        socket = context.socket(zmq.PULL)
        socket.curve_secretkey = "}vxNPm8lOJT1yvqu7-A<m<w>7OZ1ok<d?Qbq+a?5"
        socket.curve_server = True
        self.zmq_tcp_port = socket.bind_to_random_port('tcp://*', min_port=40000, max_port=50000, max_tries=10)

        # Poll and wait for data from test client
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)

        # Need to notify test client that the server is ready
        self.zmq_server_listning_event.set()

        while self.test_running:
            socks = dict(poller.poll())
            if socket in socks and socks[socket] == zmq.POLLIN:
                data = socket.recv()
                self.testing_queue.put(data)
        socket.close()

class GreenThreadAuthenticator(ThreadAuthenticator):
    def __init__(self, context):
        super(GreenThreadAuthenticator, self).__init__(context)

    def start(self):
        """Start the authentication thread"""
        # create a socket to communicate with auth thread.
        self.pipe = self.context.socket(zmq.PAIR)
        self.pipe.linger = 1
        self.pipe.bind(self.pipe_endpoint)
        self.thread = GreenAuthenticationThread(self.context, self.pipe_endpoint, encoding=self.encoding, log=self.log)
        self.thread.start()

class GreenAuthenticationThread(AuthenticationThread):
    def __init__(self, context, endpoint, encoding='utf-8', log=None, authenticator=None):
        super(GreenAuthenticationThread, self).__init__(context, endpoint, encoding='utf-8', log=None, authenticator=None)

    def run(self):
        """ Start the Authentication Agent thread task """
        self.authenticator.start()
        zap = self.authenticator.zap_socket
        poller = zmq.Poller()
        poller.register(self.pipe, zmq.POLLIN)
        poller.register(zap, zmq.POLLIN)
        while True:
            try:
                socks = dict(poller.poll())
            except zmq.ZMQError:
                break  # interrupted

            if self.pipe in socks and socks[self.pipe] == zmq.POLLIN:
                terminate = self._handle_pipe()
                if terminate:
                    break

            if zap in socks and socks[zap] == zmq.POLLIN:
                self._handle_zap()
        self.pipe.close()
        self.authenticator.stop()

# this file double-poses as a mock zmq server used for manual testing
if __name__ == '__main__':
    context = zmq.Context()

    # Authenticator runs in different greenlet.
    auth = GreenThreadAuthenticator(context)
    auth.start()
    auth.allow('127.0.0.1')
    auth.configure_curve(domain='*', location='zmq_public_keys')

    # Bind our mock zmq pull server
    socket = context.socket(zmq.PULL)
    socket.curve_secretkey = "}vxNPm8lOJT1yvqu7-A<m<w>7OZ1ok<d?Qbq+a?5"
    socket.curve_server = True
    port = 4123
    socket.bind('tcp://*:{0}'.format(port))
    print '[*] Heralding test zmq puller started on port {0}\n'

    # Poll and wait for data from test client
    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)

    pp = pprint.PrettyPrinter(indent=1)
    try:
        while True:
            socks = dict(poller.poll())
            if socket in socks and socks[socket] == zmq.POLLIN:
                topic, data = socket.recv().split(' ', 1)
                data = json.loads(data)
                print '[+] Got data at {0}:'.format(datetime.datetime.now())
                pp.pprint(data)
    finally:
        socket.close()
