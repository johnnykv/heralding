# Copyright (C) 2018 Johnny Vestergaard <jkv@unixcluster.dk>
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

import heralding.misc

import logging
import zmq
import json

from heralding.reporting.base_logger import BaseLogger

logger = logging.getLogger(__name__)


class CuriosumIntegration(BaseLogger):
    def __init__(self, zmq_socket='tcp://*:23400'):
        super(CuriosumIntegration, self).__init__()

        context = heralding.misc.zmq_context
        self.socket = context.socket(zmq.PUSH)
        self.socket.bind(zmq_socket)

    def loggerStopped(self):
        self.socket.close()

    def handle_session_log(self, data):
        message = {
            'SessionID': str(data['session_id']),
            'DstPort': data['destination_port'],
            'SrcIP': data['source_ip'],
            'SrcPort': data['source_port'],
            'SessionEnded': data['session_ended']}
        self.socket.send_string('{0} {1}'.format('session_ended', json.dumps(message)))

    def handle_listen_ports(self, data): 
        # TODO: This message should be sent every 5 second to handle restarts of curiosum 
        self.socket.send_string('{0} {1}'.format('listen_ports', json.dumps(data)))
