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
import queue
import logging

import heralding.misc
from heralding.misc.socket_names import SocketNames

logger = logging.getLogger(__name__)


class ReportingRelay:
    _logQueue = None

    def __init__(self):
        # we are singleton
        assert ReportingRelay._logQueue is None
        ReportingRelay._logQueue = queue.Queue(maxsize=10000)

        self.enabled = True

        context = heralding.misc.zmq_context
        self.internalReportingPublisher = context.socket(zmq.PUB)

    @staticmethod
    def logAuthAttempt(data):
        ReportingRelay._logQueue.put({'message_type': 'auth',
                                      'content': data})

    @staticmethod
    def logSessionInfo(data):
        if ReportingRelay._logQueue is not None:
            ReportingRelay._logQueue.put({'message_type': 'session_info',
                                          'content': data})

    @staticmethod
    def logListenPorts(data):
        if ReportingRelay._logQueue is not None:
            ReportingRelay._logQueue.put({'message_type': 'listen_ports',
                                          'content': data})

    def start(self):
        self.internalReportingPublisher.bind(SocketNames.INTERNAL_REPORTING.value)

        while self.enabled or ReportingRelay._logQueue.qsize() > 0:
                try:
                    data = ReportingRelay._logQueue.get(timeout=0.5)
                    self.internalReportingPublisher.send_pyobj(data)
                except queue.Empty:
                    pass

        # None signals 'going down' to listeners
        self.internalReportingPublisher.send_pyobj(None)
        self.internalReportingPublisher.close()

        # None is also used to signal we are all done
        ReportingRelay._logQueue = None

    def stop(self):
        self.enabled = False
