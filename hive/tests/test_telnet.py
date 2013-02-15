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

import unittest
from hive.capabilities import telnet
from hive.models.session import Session
from hive.models.authenticator import Authenticator


class Telnet_Tests(unittest.TestCase):
    def test_initial_session(self):
        """Tests if the basic parts of the session is filled correctly"""

        sessions = {}

        #provide valid login/pass to authenticator
        authenticator = Authenticator({'james': 'bond'})
        Session.authenticator = authenticator

        sut = telnet.telnet(sessions, 23)

        #dont really care about the socket at this point (None...)
        #TODO: mock the socket!
        try:
            sut.handle(None, ['192.168.1.200', 51000])
        except AttributeError:
            #because socket is not set
            pass

        #expect a single entry in the sessions dict
        self.assertEqual(1, len(sessions))
        session = sessions.values()[0]
        self.assertEqual('telnet', session.protocol)
        self.assertEqual(23, session.honey_port)
        self.assertEquals('192.168.1.200', session.attacker_ip)
        self.assertEqual(51000, session.attacker_source_port)


if __name__ == '__main__':
    unittest.main()