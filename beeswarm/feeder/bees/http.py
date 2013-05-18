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

import random
import httplib
import base64
import logging
from datetime import datetime

from beeswarm.feeder.bees.clientbase import ClientBase


class http(ClientBase):

    def __init__(self, sessions):
        super(http, self).__init__(sessions)

    def do_session(self, login, password, server_host, server_port, my_ip):

        session = self.create_session(login, password, server_host, server_port, my_ip)

        self.sessions[session.id] = session

        logging.debug(
            'Sending %s honeybee to %s:%s. (bee id: %s)' % ('http', server_host, server_port, session.id))

        # TODO: Automatically detect files in the Hive VFS
        url_list = ['/base.html']  # List of valid URLs in the Hive

        try:
            client = httplib.HTTPConnection(server_host, server_port)
            client.putrequest('GET', random.choice(url_list))
            session.source_port = client.sock.getsockname()[1]
            auth_string = login + ':' + password
            client.putheader('Authorization', 'Basic ' + base64.b64encode(auth_string))
            client.endheaders()
            session.did_connect = True
            response = client.getresponse()
        except:
            logging.debug('Caught exception, unable to connect.')
        else:
            if response.status == 200:
                session.did_login = True
            session.timestamp = datetime.now()
        finally:
            session.alldone = True

