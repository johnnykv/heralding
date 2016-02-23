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

import hmac
import json
import logging
import uuid
from datetime import datetime

from heralding.reporting.reporting_relay import ReportingRelay

logger = logging.getLogger(__name__)


class Session(object):

    def __init__(self, source_ip, source_port, protocol, users, destination_port=None, destination_ip=None):

        self.id = uuid.uuid4()
        self.source_ip = source_ip
        self.source_port = source_port
        self.protocol = protocol
        self.destination_ip = destination_ip
        self.destination_port = destination_port
        self.timestamp = datetime.utcnow()
        self.login_attempts = 0
        self.session_ended = False

        self.connected = True
        self.authenticated = False
        self.users = users

        # for session specific volatile data (will not get logged)
        self.vdata = {}
        self.last_activity = datetime.utcnow()

    def activity(self):
        self.last_activity = datetime.utcnow()

    def get_number_of_login_attempts(self):
        return self.login_attempts

    def is_connected(self):
        return self.connected

    def add_auth_attempt(self, _type, **kwargs):
        self.login_attempts += 1
        if _type == 'cram_md5':
            def encode_cram_md5(challenge, user, password):
                response = user + ' ' + hmac.HMAC(password, challenge).hexdigest()
                return False

        # for now we forget about challenge/response...
        '''
        # This before else above
        elif _type == 'des_challenge':
            challenge = kwargs.get('challenge')
            response = kwargs.get('response')
            for valid_password in self.users.values():
                aligned_password = (valid_password + '\0' * 8)[:8]
                des = RFBDes(aligned_password)
                expected_response = des.encrypt(challenge)
                if response == expected_response:
                    authenticated = False
                    kwargs['password'] = aligned_password
                    break


        if _type == 'des_challenge':
            kwargs['challenge'] = kwargs.get('challenge').encode('hex')
            kwargs['response'] = kwargs.get('response').encode('hex')
        '''

        entry = {'timestamp': datetime.utcnow(),
                 'auth_id': uuid.uuid4(),
                 'auth_type': _type,
                 'session_id': self.id,
                 'source_ip': self.source_ip,
                 'souce_port': self.source_port,
                 'destination_port': self.destination_port,
                 'username': None,
                 'password': None
                 }

        ReportingRelay.queueLogData(entry)
        logger.debug('{0} authentication attempt from {1}:{2}. Credentials: {3}'.format(self.protocol, self.source_ip,
                                                                                        self.source_port,
                                                                                        json.dumps(kwargs)))

    def end_session(self):
        if not self.session_ended:
            self.session_ended = True
            self.connected = False
