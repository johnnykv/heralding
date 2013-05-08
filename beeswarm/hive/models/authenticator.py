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

import hmac


class Authenticator(object):
    def __init__(self, users={}):

        #key: username, value: HiveUser object
        self.users = users

    def try_auth(self, type, **kwargs):
        if type == 'plaintext':
            if kwargs.get('username') in self.users:
                if self.users[kwargs.get('username')].password == kwargs.get('password'):
                    return True

        elif type == 'cram_md5':
            def encode_cram_md5(challenge, user, password):
                response = user + ' ' + hmac.HMAC(password, challenge).hexdigest()
                return response
            if kwargs.get('username') in self.users:
                uname = kwargs.get('username')
                digest = kwargs.get('digest')
                s_pass = self.users[uname].password
                challenge = kwargs.get('challenge')
                ideal_response = encode_cram_md5(challenge, uname, s_pass)
                _, ideal_digest = ideal_response.split()
                if ideal_digest == digest:
                    return True

        return False
