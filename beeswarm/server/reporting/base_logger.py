# Copyright (C) 2014 Johnny Vestergaard <jkv@unixcluster.dk>
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

import logging
from gevent import Greenlet
from beeswarm.shared.socket_enum import SocketNames

import zmq.green as zmq

import beeswarm


logger = logging.getLogger(__name__)


class BaseLogger(Greenlet):
    def __init__(self, options):
        Greenlet.__init__(self)
        self.enabled = True
        self.options = options

    def _run(self):
        context = beeswarm.shared.zmq_context
        receiving_socket = context.socket(zmq.SUB)
        receiving_socket.connect(SocketNames.PROCESSED_SESSIONS.value)
        receiving_socket.setsockopt(zmq.SUBSCRIBE, '')

        poller = zmq.Poller()
        poller.register(receiving_socket, zmq.POLLIN)

        while self.enabled:
            socks = dict(poller.poll(100))
            if receiving_socket in socks and socks[receiving_socket] == zmq.POLLIN:
                topic, data = receiving_socket.recv().split(' ', 1)
                self.handle_data(topic, data)
        receiving_socket.close()

    def stop(self):
        self.enabled = False

    def handle_data(self, topic, data):
        # should be handled in child class
        raise NotImplementedError("Please implement this method")
