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

import gevent
import zmq.auth
import zmq.green as zmq
from enum import Enum
from zmq.utils import jsonapi
from zmq.utils.monitor import recv_monitor_message

import heralding.misc
from base_logger import BaseLogger

logger = logging.getLogger(__name__)


class ZmqMessageTypes(Enum):
    HERALDING_AUTH_LOG = 'HERALDING_AUTH_LOG'


class ZmqLogger(BaseLogger):
    def __init__(self):
        super(ZmqLogger, self).__init__()
        # TODO: Take this as param
        self.zmq_socket_url = "tcp://localhost:4569"
        self.enabled = True

        # TODO: auth and encryption (Curve)
        context = heralding.misc.zmq_context
        self.socket = context.socket(zmq.PUSH)

        # setup sending tcp socket
        self.socket.setsockopt(zmq.RECONNECT_IVL, 2000)


        # monitors socket and gives meaningful log messages in regards to connectivity issues
        gevent.spawn(self.monitor_worker)
        self.socket.connect(self.zmq_socket_url)

    def loggerStopped(self):
        self.socket.close()
        self.enabled = False

    def handle_log_data(self, data):
        print 'zme logger got data'
        message = "{0} {1}".format(ZmqMessageTypes.HERALDING_AUTH_LOG.value, jsonapi.dumps(data))
        self.socket.send(message)

    def monitor_worker(self):
        monitor_socket = self.socket.get_monitor_socket()
        monitor_socket.linger = 0
        poller = zmq.Poller()
        poller.register(monitor_socket, zmq.POLLIN)
        while self.enabled:
            socks = poller.poll(1)
            # TODO: This, again, why?
            gevent.sleep(0.01)
            if len(socks) > 0:
                data = recv_monitor_message(monitor_socket)
                event = data['event']
                if event == zmq.EVENT_CONNECTED:
                    logger.info('Connected to {0}'.format(self.zmq_socket_url))
                elif event == zmq.EVENT_DISCONNECTED:
                    logger.warning(
                        'Disconnected from {0}, will reconnect in {1} seconds.'.format(self.zmq_socket_url, 5))
            gevent.sleep()
