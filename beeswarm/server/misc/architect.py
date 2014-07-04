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
import math

import gevent
import zmq.green as zmq

from beeswarm.server.db import database_setup
from beeswarm.server.db.entities import Drone, Client, Honeypot
from beeswarm.shared.message_enum import Messages

logger = logging.getLogger(__name__)


class Architect(object):
    def __init__(self, honeypot_ratio):
        self.honeypot_ratio = honeypot_ratio

    def generate_architecture(self):
        db_session = database_setup.get_session()
        drones = db_session.query(Drone).all()
        # following if/elif/else if full auto mode
        drone_count = len(drones)
        if drone_count == 0:
            logger.debug('Not able to generate architecture because only one drone exist.')
        elif drone_count == 1:
            logger.debug('Only one drone exists, this will get configured as a honeypot.')
            # TODO: Configure as honeypot
        else:
            number_of_honeypot = math.ceil(drone_count / self.honeypot_ratio)
            number_of_clients = drone_count - number_of_honeypot
            logger.debug('Generating architecture with {0} honeypots, {1} clients using a {2} rati.'
                         .format(number_of_honeypot, number_of_clients, self.honeypot_ratio))

            # Algo to distribute honeypots, clients and capabilities.
            pass

        # TODO: Semi auto mode, only configure unconfigured.
        # TODO: Also maybe reset button on drones pages. Mark drones to reset.
        # TODO: Would be nice to be display the deceptions configuration as a graph using d3.js

    def brodcast_arthitecture(self, configuration):
        db_session = database_setup.get_session()
        drones = db_session.query(Drone)
        for drone in drones:
            self.droneCommandsReceiver.send('{0} {1} {2}'.format(drone.id, Messages.CONFIG_ARCHITECTURE, configuration))

