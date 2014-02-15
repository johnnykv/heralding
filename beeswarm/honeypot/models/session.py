# Copyright (C) 2013 Johnny Vestergaard <jkv@unixcluster.dk>
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

import uuid
import logging
from datetime import datetime
from beeswarm.shared.models.base_session import BaseSession


logger = logging.getLogger(__name__)


class Session(BaseSession):
    authenticator = None
    default_timeout = 25
    honeypot_id = None

    def __init__(self, source_ip, source_port, protocol, socket, destination_port=None, destination_ip=None):

        super(Session, self).__init__(protocol, source_ip, source_port, destination_ip, destination_port)

        assert Session.authenticator is not None

        self.connected = True
        self.authenticated = False
        self.honeypot_id = Session.honeypot_id

        #for session specific volatile data (will not get logged)
        self.vdata = {}
        self.socket = socket

    def try_auth(self, _type, **kwargs):

        if Session.authenticator.try_auth(_type, **kwargs):
            self.authenticated = True
            self.add_auth_attempt(_type, True, **kwargs)
            return True
        else:
            self.add_auth_attempt(_type, False, **kwargs)
            return False

    def activity(self):
        self.last_activity = datetime.utcnow()

    def last_activity(self):
        return self.socket.last_update()

    def is_connected(self):
        return self.connected
