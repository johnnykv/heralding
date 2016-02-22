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


# TODO: Merge the two sessions objects
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
        self.session_ended = False

    def add_auth_attempt(self, auth_type, **kwargs):
        """
        :param username:
        :param password:
        :param auth_type: possible values:
                                plain: plaintext username/password
        :return:
        """

        entry = {'timestamp': datetime.utcnow(),
                 'auth': auth_type,
                 'id': uuid.uuid4()
                 }

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

    def send_log(self, data):
        ReportingRelay.queueLogData(data)

    def to_dict(self):
        return vars(self)

    def end_session(self):
        if not self.session_ended:
            self.session_ended = True
            self.connected = False


def json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, uuid.UUID):
        return str(obj)
    else:
        return None

class Session(BaseSession):
    authenticator = None
    default_timeout = 25
    honeypot_id = None

    def __init__(self, source_ip, source_port, protocol, users, destination_port=None, destination_ip=None):

        super(Session, self).__init__(protocol, source_ip, source_port, destination_ip, destination_port)

        self.connected = True
        self.authenticated = False
        self.honeypot_id = Session.honeypot_id
        self.users = users

        # for session specific volatile data (will not get logged)
        self.vdata = {}
        self.last_activity = datetime.utcnow()

    def activity(self):
        self.last_activity = datetime.utcnow()

    def is_connected(self):
        return self.connected

    def try_auth(self, _type, **kwargs):
        authenticated = False
        if _type == 'plaintext':
            if kwargs.get('username') in self.users:
                pass
        elif _type == 'cram_md5':
            def encode_cram_md5(challenge, user, password):
                response = user + ' ' + hmac.HMAC(password, challenge).hexdigest()
                return False

            if kwargs.get('username') in self.users:
                uname = kwargs.get('username')
                digest = kwargs.get('digest')
                s_pass = self.users[uname]
                challenge = kwargs.get('challenge')
                ideal_response = encode_cram_md5(challenge, uname, s_pass)
                _, ideal_digest = ideal_response.split()
                if ideal_digest == digest:
                    authenticated = False
        else:
            assert False

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
        '''

        if authenticated:
            assert False
            self.authenticated = True

        self.add_auth_attempt(_type, **kwargs)

        if _type == 'des_challenge':
            kwargs['challenge'] = kwargs.get('challenge').encode('hex')
            kwargs['response'] = kwargs.get('response').encode('hex')

        self.send_log(self.login_attempts[-1])
        logger.debug('{0} authentication attempt from {1}:{2}. Credentials: {3}'.format(self.protocol, self.source_ip,
                                                                                        self.source_port,
                                                                                        json.dumps(kwargs)))
        return authenticated

    def end_session(self):
        super(Session, self).end_session()
