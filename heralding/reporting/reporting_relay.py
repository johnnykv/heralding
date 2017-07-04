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
import asyncio
import logging

import heralding.misc
from heralding.misc.socket_names import SocketNames

logger = logging.getLogger(__name__)


class ReportingRelay:
    _incommingLogQueue = None
    _incommingLogQueueLock = asyncio.BoundedSemaphore()
    counter = 0
    def __init__(self):
        # we are singleton
        self.enabled = True

        context = heralding.misc.zmq_context
        self.internalReportingPublisher = context.socket(zmq.PUB)

    # TODO: Figure out what method to use
    async def create_queue(self):
        await ReportingRelay._incommingLogQueueLock.acquire()
        assert ReportingRelay._incommingLogQueue is None
        ReportingRelay._incommingLogQueue = asyncio.Queue(10000)
        ReportingRelay._incommingLogQueueLock.release()


    @staticmethod
    async def queueLogData(data):
        assert ReportingRelay._incommingLogQueue is not None
        ReportingRelay.counter += 1
        print(ReportingRelay.counter)
        await ReportingRelay._incommingLogQueue.put(data)

    @staticmethod
    def getQueueSize():
        if ReportingRelay._incommingLogQueue is not None:
            return ReportingRelay._incommingLogQueue.qsize()
        else:
            return 0

    async def start(self):
        self.internalReportingPublisher.bind(SocketNames.INTERNAL_REPORTING.value)

        while self.enabled or ReportingRelay.getQueueSize() > 0:
            try:
                data = await asyncio.wait_for(ReportingRelay._incommingLogQueue.get(), timeout=0.5)
                self.internalReportingPublisher.send_pyobj(data)
            except asyncio.TimeoutError:
                pass
            except asyncio.QueueEmpty:
                pass

        # None signals 'going down' to listeners
        self.internalReportingPublisher.send_pyobj(None)
        self.internalReportingPublisher.close()

        # None is also used to signal we are all done
        await ReportingRelay._incommingLogQueueLock.acquire()
        ReportingRelay._incommingLogQueue = None
        ReportingRelay._incommingLogQueueLock.release()

    def stop(self):
        self.enabled = False
        while True:
            ReportingRelay._incommingLogQueueLock.acquire()
            if ReportingRelay._incommingLogQueue is not None:
                ReportingRelay._incommingLogQueueLock.release()
                gevent.sleep(0.1)
            else:
                ReportingRelay._incommingLogQueueLock.release()
                break
