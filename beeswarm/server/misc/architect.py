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

from beeswarm.server.db import database_setup
from beeswarm.server.db.entities import Drone, Client, Honeypot
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
        db_session = database_setup.get_session()
        drones = db_session.query(Drone).all()
        # following if/elif/else if full auto mode
        if len(drones) == 0:
            return
        elif len(drones) == 1:
            # TODO: Configure as honeypot
            pass
        else:
            # Algo to distribute honeypots, clients and capabilities.
            pass

        # TODO: Semi auto more, only configure unconfigured.
        # TODO: Also maybe reset button on drones pages. Mark drones to reset.
        # TODO: Would be nice to be display the deceptions configuration as a graph using d3.js

    def brodcast_arthitecture(self, configuration):
        db_session = database_setup.get_session()
        drones = db_session.query(Drone)
        for drone in drones:
            self.droneCommandsReceiver.send('{0} {1} {2}'.format(drone.id, Messages.CONFIG_ARCHITECTURE, configuration))

