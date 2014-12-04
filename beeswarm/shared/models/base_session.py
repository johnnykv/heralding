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
import json
from datetime import datetime

import zmq.green as zmq
import beeswarm
from beeswarm.shared.socket_enum import SocketNames
from beeswarm.shared.message_enum import Messages


logger = logging.getLogger(__name__)


class BaseSession(object):
    def __init__(self, protocol, source_ip=None, source_port=None, destination_ip=None, destination_port=None):
        self.id = uuid.uuid4()
        self.source_ip = source_ip
        self.source_port = source_port
        self.protocol = protocol
        self.destination_ip = destination_ip
        self.destination_port = destination_port
        self.timestamp = datetime.utcnow()
        self.login_attempts = []
        self.transcript = []
        self.session_ended = False


        context = beeswarm.shared.zmq_context
        self.socket = context.socket(zmq.PUSH)
        self.socket.connect(SocketNames.SERVER_RELAY)

    def add_auth_attempt(self, auth_type, successful, **kwargs):
        """
        :param username:
        :param password:
        :param auth_type: possible values:
                                plain: plaintext username/password
        :return:
        """

        entry = {'timestamp': datetime.utcnow(),
                 'auth': auth_type,
                 'id': uuid.uuid4(),
                 'successful': successful}

        log_string = ''
        for key, value in kwargs.iteritems():
            if key == 'challenge' or key == 'response':
                entry[key] = repr(value)
            else:
                entry[key] = value
                log_string += '{0}:{1}, '.format(key, value)

        self.login_attempts.append(entry)

    def get_number_of_login_attempts(self):
        return len(self.login_attempts)

    def _add_transcript(self, direction, data):
        self.transcript.append({'timestamp': datetime.utcnow(), 'direction': direction, 'data': data})

    def transcript_incoming(self, data):
        self._add_transcript('incoming', data)

    def transcript_outgoing(self, data):
        self._add_transcript('outgoing', data)

    def send_log(self, type, in_data):
        data = json.dumps(in_data, default=json_default, ensure_ascii=False)
        self.socket.send('{0} {1} {2}'.format(type, self.honeypot_id, data))

    def to_dict(self):
        return vars(self)

    def end_session(self, session_type):
        if not self.session_ended:
            self.session_ended = True
            self.send_log(session_type, self.to_dict())
            self.connected = False



def json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, uuid.UUID):
        return str(obj)
    else:
        return None