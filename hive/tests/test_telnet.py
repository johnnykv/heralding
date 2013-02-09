# Copyright (C) 2012 Johnny Vestergaard <jkv@unixcluster.dk>
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

import sys

sys.path.append('../') #to be able to import capabilities

import unittest
from capabilities import telnet
from datetime import datetime


class Telnet_Tests(unittest.TestCase):
    def test_sessionkeys(self):
        """Tests if the session dicts initially contains the correct keys"""

        sessions = {}
        accounts = {}
        sut = telnet.telnet(sessions, accounts)

        #dont really care about the socket at this point (None...)
        #TODO: mock the socket!
        try:
            sut.handle(None, ['192.168.1.200', 51000])
        except:
            pass

        session = sessions[sessions.keys()[0]]
        self.assertTrue(len(str(session['id'])) > 20)

        delta = datetime.utcnow() - session['timestamp']
        self.assertTrue(delta.seconds < 2)

        delta = datetime.utcnow() - session['last_activity']
        self.assertTrue(delta.seconds < 2)

        self.assertTrue(session['attacker_ip'] == '192.168.1.200')
        self.assertTrue(session['attacker_src_port'] == 51000)

        #just check that we have the keys
        self.assertTrue('connected' in session)
        self.assertTrue('login_tries' in session)

        self.assertEqual(session['protocol'], 'telnet')
        self.assertEqual(session['protocol_port'], telnet.telnet.port)


if __name__ == '__main__':
    unittest.main()