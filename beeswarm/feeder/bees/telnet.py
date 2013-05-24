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

import logging
import telnetlib

from beeswarm.feeder.bees.clientbase import ClientBase


class telnet(ClientBase):

    def __init__(self, sessions):
        super(telnet, self).__init__(sessions)

    def do_session(self, login, password, server_host, server_port, my_ip):

        session = self.create_session(login, password, server_host, server_port, my_ip)
        self.sessions[session.id] = session
        logging.debug(
            'Sending %s honeybee to %s:%s. (bee id: %s)' % ('telnet', server_host, server_port, session.id))

        try:
            client = telnetlib.Telnet(server_host, server_port)
            session.did_connect = True
            session.source_port = client.sock.getsockname()[1]
            client.read_until('Username: ')
            client.write(login + '\r\n')
            client.read_until('Password: ')
            client.write(password + '\r\n')
            while True:
                current_data = client.read_until('\r\n')
                if 'Invalid' not in current_data:
                    if 'Logged in.' not in current_data:
                        # We got some useless string from the server, so get more data and hope
                        # that the next line will contain a valid response
                        continue
                    else:
                        session.did_login = True
                        break
                else:
                    raise InvalidLogin
        except Exception as err:
            logging.debug('Caught exception: %s (%s)' % (err, str(type(err))))
        else:
            client.read_until('$ ')
            client.write('ls\r\n')
            client.read_until('$ ')
            logging.debug('Telnet file listing successful.')
            client.write('exit\r\n')
            client.read_all()
            client.close()
        finally:
            session.alldone = True


class InvalidLogin(Exception):
    pass