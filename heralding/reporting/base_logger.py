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

import logging

import zmq.green as zmq
from gevent import Greenlet

import heralding.misc
from heralding.misc.socket_names import SocketNames

logger = logging.getLogger(__name__)


class BaseLogger(Greenlet):
    def __init__(self):
        Greenlet.__init__(self)
        self.enabled = True

    def _run(self):
        context = heralding.misc.zmq_context

        internal_reporting_socket = context.socket(zmq.SUB)
        internal_reporting_socket.connect(SocketNames.INTERNAL_REPORTING.value)
        internal_reporting_socket.setsockopt(zmq.SUBSCRIBE, '')

        poller = zmq.Poller()
        poller.register(internal_reporting_socket, zmq.POLLIN)

        while self.enabled:
            socks = dict(poller.poll(500))
            if internal_reporting_socket in socks and socks[internal_reporting_socket] == zmq.POLLIN:
                data = internal_reporting_socket.recv_pyobj()
                assert isinstance(data, dict)
                self.handle_log_data(data)
        internal_reporting_socket.close()

    def stop(self):
        self.enabled = False

    def handle_log_data(self, data):
        # should be handled in child class
        raise NotImplementedError("Please implement this method")

    def loggerStopped(self):
        pass
