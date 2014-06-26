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
import gevent

import zmq.green as zmq

from beeswarm.shared.message_enum import Messages

logger = logging.getLogger(__name__)


class Architect(gevent.greenlet):
    def __init__(self):
        gevent.Greenlet.__init__(self)

        context = zmq.Context()
        self.droneCommandsReceiver = context.socket(zmq.PUSH)
        self.droneCommandsReceiver.connect('ipc://droneCommandReceiver')
        self.enabled = True

    def _run(self):
        while True:
            # TODO: wait for poke from someone
            gevent.sleep(5)
            architecture_document = self._generate_architecture()
            self.brodcast_arthitecture(architecture_document)

    def _stop(self):
        self.enabled = False
        self.droneCommandsReceiver.close()

    def _generate_architecture(self):
        # TODO: - Pair honeypots and clients
        #       - Assign credentials for bait session
        #       - Figure out timing issues
        #       - There should be two modes selectable by the user:
        #         1. Full auto. Everything is deleted and reconfigured
        #         2. Semi auto. Everything not configured by the user is configured as a best effort.
        pass

    def brodcast_arthitecture(self, configuration):
        # TODO: DB query
        for drone in all_drones:
            self.droneCommandsReceiver.send('{0} {1} {2}'.format(drone.id, Messages.CONFIG_ARCHITECTURE, configuration))

