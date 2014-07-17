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
            entry[key] = value
            log_string += '{0}:{1}, '.format(key, value)

        self.login_attempts.append(entry)

    def _add_transcript(self, direction, data):
        self.transcript.append({'timestamp': datetime.utcnow(), 'direction': direction, 'data': data})

    def transcript_incoming(self, data):
        self._add_transcript('incoming', data)

    def transcript_outgoing(self, data):
        self._add_transcript('outgoing', data)

    def to_dict(self):
        return vars(self)