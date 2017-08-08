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
    _incommingLogQueue = None

    def __init__(self):
        # we are singleton
        assert ReportingRelay._incommingLogQueue is None
        ReportingRelay._incommingLogQueue = queue.Queue(maxsize=10000)

        self.enabled = True

        context = heralding.misc.zmq_context
        self.internalReportingPublisher = context.socket(zmq.PUB)

    @staticmethod
    def queueLogData(data):
        assert ReportingRelay._incommingLogQueue is not None
        ReportingRelay._incommingLogQueue.put(data)

    @staticmethod
    def getQueueSize():
        if ReportingRelay._incommingLogQueue is not None:
            return ReportingRelay._incommingLogQueue.qsize()
        else:
            return 0

    def start(self):
        self.internalReportingPublisher.bind(SocketNames.INTERNAL_REPORTING.value)

        while self.enabled or ReportingRelay.getQueueSize() > 0:
            try:
                data = ReportingRelay._incommingLogQueue.get(timeout=0.5)
                self.internalReportingPublisher.send_pyobj(data)
            except queue.Empty:
                pass

        # None signals 'going down' to listeners
        self.internalReportingPublisher.send_pyobj(None)
        self.internalReportingPublisher.close()

        # None is also used to signal we are all done
        ReportingRelay._incommingLogQueue = None

    def stop(self):
        self.enabled = False
