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

import json
import logging
import os
import tempfile
import shutil
import random

from gevent import Greenlet
import zmq.green as zmq
from zmq.auth.certs import create_certificates

import beeswarm
from beeswarm.shared.message_enum import Messages
from beeswarm.server.db import database_setup
from beeswarm.server.db.entities import Client, Honeypot, Drone, DroneEdge, BaitUser
from beeswarm.shared.socket_enum import SocketNames

class BaseActor(Greenlet):
    def __init__(self, config_file, work_dir, command_requests_only=False):
        Greenlet.__init__(self)
        self.config_file = os.path.join(work_dir, config_file)
        self.commands_only = command_requests_only
        if not os.path.exists(self.config_file):
            self.config = {}
            self._save_config_file()
        self.config = json.load(open(self.config_file, 'r'))
        self.work_dir = work_dir

        context = beeswarm.shared.zmq_context
        self.config_commands = context.socket(zmq.REP)
        self.drone_command_receiver = None

        if not self.commands_only:
            self.drone_command_receiver = context.socket(zmq.PUSH)

        self.enabled = True
