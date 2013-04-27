# Copyright (C) 2013 Aniket Panse <contact@aniketpanse.in>
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
from datetime import datetime


class BeeSession(object):

    def __init__(self, protocol, login, password, hive_host, hive_port, my_ip):

        self.id = uuid.uuid4()
        self.protocol = protocol
        self.login = login
        self.password = password
        self.server_host = hive_host
        self.server_port = hive_port
        self.timestamp = datetime.utcnow()
        self.did_connect = False
        self.did_login = False
        self.alldone = False
        self.did_complete = False
        self.protocol_data = {}
        self.my_ip = my_ip

    def to_dict(self):
        selfdict = {
            'id': self.id,
            'protocol': self.protocol,
            'login': self.login,
            'password': self.password,
            'server_host': self.server_host,
            'server_port': self.server_port,
            'timestamp': self.timestamp,
            'did_connect': self.did_connect,
            'did_login': self.did_login,
            'did_complete': self.did_complete,
            'protocol_data': self.protocol_data
        }
        return selfdict