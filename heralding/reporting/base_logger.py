# Copyright (C) 2017 Johnny Vestergaard <jkv@unixcluster.dk>
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

import zmq
import logging

import heralding.misc
from heralding.misc.socket_names import SocketNames

logger = logging.getLogger(__name__)


class BaseLogger:
    def __init__(self):
        self.enabled = True

    def start(self):
        context = heralding.misc.zmq_context

        internal_reporting_socket = context.socket(zmq.SUB)
        internal_reporting_socket.connect(SocketNames.INTERNAL_REPORTING.value)
        internal_reporting_socket.setsockopt(zmq.SUBSCRIBE, b'')

        poller = zmq.Poller()
        poller.register(internal_reporting_socket, zmq.POLLIN)
        while self.enabled:
            socks = dict(poller.poll(500))
            self._execute_regulary()
            if internal_reporting_socket in socks and socks[internal_reporting_socket] == zmq.POLLIN:
                data = internal_reporting_socket.recv_pyobj()
                # if None is received, this means that ReportingRelay is going down
                if not data:
                    self.stop()
                elif data['message_type'] == 'auth':
                    self.handle_auth_log(data['content'])
                elif data['message_type'] == 'session_info':
                    self.handle_session_log(data['content'])
                elif data['message_type'] == 'listen_ports':
                    self.handle_listen_ports(data['content'])
                elif data['message_type'] == 'stat':
                    self.handle_stat_log(data['content'])
        internal_reporting_socket.close()
        # at this point we know no more data will arrive.
        self.loggerStopped()

    def stop(self):
        self.enabled = False

    def handle_auth_log(self, data):
        # should be handled in child class
        pass

    def handle_session_log(self, data):
        # implement if needed
        pass

    def handle_listen_ports(self, data):
        # implement if needed
        pass

    def handle_stat_log(self, data):
        # implement if needed
        pass

    def _execute_regulary(self):
        # if implemented this method will get called regulary
        pass

    # called after we are sure no more data is received
    # override this to close filesockets, etc.
    def loggerStopped(self):
        pass
