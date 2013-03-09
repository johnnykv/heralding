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

import poplib
from datetime import datetime
import uuid
import h_socket
import logging

from clientbase import ClientBase


class pop3(ClientBase):
    def __init__(self, sessions):
        self.sessions = sessions

    def do_session(self, login, password, server_host, server_port, my_ip):
        """Login, RETR and DELE all messages"""

        session = {
        'id': uuid.uuid4(),
        'protocol': 'pop3',
        'my_ip': my_ip,
        'login': login,
        'password': password,
        'server_host': server_host,
        'server_port': server_port,
        'timestamp': datetime.utcnow(),
        'did_connect': False,
        'did_login': False,
        'did_complete': False,
        'protocol_data': {}
        }

        self.sessions[session['id']] = session

        try:
            logging.debug(
                'Sending %s honeybee to %s:%s. (bee id: %s)' % ('pop3', server_host, server_port, session['id']))
            conn = poplib.POP3(server_host, server_port)
            banner = conn.getwelcome()
            session['protocol_data']['banner'] = banner
            session['did_connect'] = True

            conn.user(login)
            conn.pass_(password)
            session['did_login'] = True
            session['timestamp'] = datetime.utcnow()
        except (poplib.error_proto, h_socket.error) as err:
            logging.debug('Caught exception: %s (%s)' % (err, str(type(err))))
        else:
            list_entries = conn.list()[1]
            for entry in list_entries:
                index, octets = entry.split(' ')
                conn.retr(index)
                conn.dele(index)
            logging.debug('Found and deleted %i messages on %s' % (len(list_entries), server_host))
            conn.quit()
            session['did_complete'] = True
        finally:
            session['alldone'] = True
			