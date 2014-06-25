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

import logging
import uuid
import json
from datetime import datetime

import zmq.green as zmq
import zmq.auth


logger = logging.getLogger(__name__)


class ServerLogger(object):
    def __init__(self, message_type):
        context = zmq.Context()
        self.socket = context.socket(zmq.PUSH)
        self.socket.connect('ipc://serverRelay')
        self.message_type = message_type

    def log(self, session):
        data = json.dumps(session.to_dict(), default=json_default, ensure_ascii=False)
        self.socket.send('{0} {1}'.format(self.message_type, data))


def json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, uuid.UUID):
        return str(obj)
    else:
        return None
