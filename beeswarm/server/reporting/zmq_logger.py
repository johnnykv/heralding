# Copyright (C) 2015 Johnny Vestergaard <jkv@unixcluster.dk>
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

# This logger transports all processed and live sessions out of the beeswarm
# system using ZMQ

import zmq.green as zmq

from base_logger import BaseLogger
import beeswarm.shared


class ZmqLogger(BaseLogger):
    def __init__(self, zmq_socket):
        super(ZmqLogger, self).__init__({})

        context = beeswarm.shared.zmq_context
        self.outgoing_socket = context.socket(zmq.PUSH)
        self.outgoing_socket.bind(zmq_socket)

    def handle_processed_session(self, topic, data):
        self.outgoing_socket.send('{0} {1}'.format(topic, data))

    def handle_live_session_part(self, topic, data):
        self.outgoing_socket.send('{0} {1}'.format(topic, data))