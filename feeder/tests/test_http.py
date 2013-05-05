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

import gevent.monkey
from hive.models.user import HiveUser

gevent.monkey.patch_all()
from gevent.server import StreamServer
from hive.helpers.common import create_socket
from hive.capabilities import http as hive_http
from feeder.bees import http as bee_http

import unittest

from feeder.models.session import BeeSession
from hive.models.authenticator import Authenticator
from hive.models.session import Session


class HTTP_Test(unittest.TestCase):

    def test_login(self):
        """ Tests if HTTP bee can login to the http capability.
        """
        authenticator = Authenticator({'test': 'test'})
        Session.authenticator = authenticator

        sessions = {}
        users = {'test': HiveUser('test', 'test')}
        cap = hive_http.http(sessions, {'enabled': 'True', 'port': 8081}, users)
        socket = create_socket(('0.0.0.0', 8081))
        srv = StreamServer(socket, cap.handle_session)
        srv.start()

        bee_info = {
            'timing': 'regular',
            'login': 'test',
            'password': 'test',
            'port': '8080',
            'server': '127.0.0.1'
        }
        beesessions = {}

        BeeSession.feeder_id = 'f51171df-c8f6-4af4-86c0-f4e163cf69e8'

        current_bee = bee_http.http(beesessions)
        current_bee.do_session(bee_info['login'], bee_info['password'], bee_info['server'],
                               bee_info['port'], '127.0.0.1')
        srv.stop()

if __name__ == '__main__':
    unittest.main()
