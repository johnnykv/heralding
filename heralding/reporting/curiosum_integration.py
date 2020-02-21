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
from datetime import datetime

from heralding.reporting.base_logger import BaseLogger

logger = logging.getLogger(__name__)


class CuriosumIntegration(BaseLogger):

  def __init__(self, port):
    super().__init__()

    zmq_socket = 'tcp://127.0.0.1:{0}'.format(port)

    context = heralding.misc.zmq_context
    self.socket = context.socket(zmq.PUSH)
    self.socket.bind(zmq_socket)
    self.listen_ports = []
    self.last_listen_ports_transmit = datetime.now()

    logger.info('Curiosum logger started using files: %s', zmq_socket)

  def loggerStopped(self):
    self.socket.close()

  def _no_block_send(self, topic, data):
    try:
      self.socket.send_string('{0} {1}'.format(topic, json.dumps(data)),
                              zmq.NOBLOCK)
    except zmq.ZMQError as e:
      logger.warning('Error while sending: %s', e)

  def handle_session_log(self, data):
    message = {
        'SessionID': str(data['session_id']),
        'DstPort': data['destination_port'],
        'SrcIP': data['source_ip'],
        'SrcPort': data['source_port'],
        'SessionEnded': data['session_ended']
    }
    self._no_block_send('session_ended', message)

  def _execute_regulary(self):
    if (datetime.now() - self.last_listen_ports_transmit).total_seconds() > 5:
      self._no_block_send('listen_ports', self.listen_ports)
      self.last_listen_ports_transmit = datetime.now()

  def handle_listen_ports(self, data):
    self.listen_ports = data
