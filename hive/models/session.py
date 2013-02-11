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

from hive.models.authenticator import Authenticator

logger = logging.getLogger(__name__)


class Session(object):

    authenticator = None

    def __init__(self, attacker_ip, attacker_s_port, protocol, honeypot_port, honeypot_ip=None):

        assert Session.authenticator is not None

        self.attacker_ip = attacker_ip
        self.attacker_source_port = attacker_s_port
        self.protocol = protocol
        self.honey_ip = honeypot_ip
        self.honey_port = honeypot_port

        self.id = uuid.uuid4()
        self.timestamp = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.is_connected = True
        #username != None means that the session is authenticated
        self.user_name = None
        #for session specific volatile data (will not get logged)
        self.vdata = {}

        self.login_attempts = []

    def try_login(self, username, password):
        self.login_attempts.append({'username': username,
                                    'password': password,
                                    'timestamp': datetime.utcnow()})
        logger.info('{0} authentication attempt from {1}. [{2}/{3}] ({4})'
        .format(self.protocol, self.attacker_ip, username, password, self.id))

        if Session.authenticator.try_auth(username, password):
            self.user_name = username
            return True
        else:
            return False

    def authenticated(self):
        """
        Returns true if the current session is authenticated
        """
        if self.user_name:
            return True
        else:
            return False

    def activity(self):
        self.last_activity = datetime.utcnow()



