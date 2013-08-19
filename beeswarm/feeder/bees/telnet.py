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
import random
import string
import telnetlib
import re
import time

from beeswarm.feeder.bees.clientbase import ClientBase
from beeswarm.feeder.bees.shared.shell import Commands


class BeeTelnetClient(telnetlib.Telnet):

    IAC = chr(255)

    def write_human(self, buffer_):
        """ Emulates human typing speed """

        if self.IAC in buffer_:
            buffer_ = buffer_.replace(self.IAC, self.IAC+self.IAC)
        self.msg("send %r", buffer_)
        for char in buffer_:
            delta = random.gauss(80, 20)
            self.sock.sendall(char)
            time.sleep(delta/1000.0)  # Convert milliseconds to seconds


class telnet(ClientBase, Commands):

    COMMAND_MAP = {
        'pwd': ['ls', 'uname', 'uptime'],
        'cd': ['ls'],
        'uname': ['uptime', 'ls'],
        'ls': ['cd', 'cat', 'pwd'],
        'cat': ['ls', 'echo', 'sudo', 'pwd'],
        'uptime': ['ls', 'echo', 'sudo', 'uname', 'pwd'],
        'echo': ['ls', 'sudo', 'uname', 'pwd'],
        'sudo': ['logout']
    }

    def __init__(self, sessions, options):
        ClientBase.__init__(self, sessions, options)
        Commands.__init__(self)
        self.client = None

    def do_session(self, my_ip):
        """ Launch one login session"""

        login = self.options['username']
        password = self.options['password']
        server_host = self.options['server']
        server_port = self.options['port']
        session = self.create_session(server_host, server_port, my_ip)
        self.sessions[session.id] = session
        logging.debug(
            'Sending %s honeybee to %s:%s. (bee id: %s)' % ('telnet', server_host, server_port, session.id))

        try:
            self.connect()
            self.login(login, password)

            #TODO: Handle failed login
            session.add_auth_attempt('plaintext', True, username=login, password=login)

            session.did_connect = True
            session.source_port = self.client.sock.getsockname()[1]
            session.did_login = True
        except Exception as err:
            logging.debug('Caught exception: %s (%s)' % (err, str(type(err))))
        else:
            while self.command_count < self.command_limit:
                self.sense()
                comm, param = self.decide()
                self.act(comm, param)
                time.sleep(10)
        finally:
            session.alldone = True

    def connect(self):
        self.client = BeeTelnetClient(self.options['server'], self.options['port'])
        self.client.set_option_negotiation_callback(self.process_options)

    def login(self, login, password):
        self.client.read_until('Username: ')
        self.client.write(login + '\r\n')
        self.client.read_until('Password: ')
        self.client.write(password + '\r\n')
        current_data = self.client.read_until('$ ', 5)
        if not current_data.endswith('$ '):
            raise InvalidLogin

    def logout(self):
        self.client.write('exit\r\n')
        self.client.read_all()
        self.client.close()

    def get_response(self):
        response = self.client.read_until('$ ', 5)
        return response

    def send_command(self, cmd):
        if self.command_count > self.command_limit:
            self.logout()
            return
        logging.debug('Sending %s command.' % cmd)
        self.command_count += 1
        self.client.write_human(cmd + '\r\n')

    def process_options(self, *args):
        """Dummy callback, used to disable options negotiations"""


class InvalidLogin(Exception):
    pass