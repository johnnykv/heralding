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

from beeswarm.shared.vnc.des import RFBDes


class VNCDecoder(object):
    def __init__(self, challenge, response, passwd_list):
        self.challenge = challenge
        self.response = response
        self.passwd_list = passwd_list

    def decode(self):
        for password in self.passwd_list:
            password = password.strip('\n')
            key = (password + '\0' * 8)[:8]
            encryptor = RFBDes(key)
            resp = encryptor.encrypt(self.challenge)
            if resp == self.response:
                return key