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
import telnetlib
import time

from beeswarm.drones.client.baits.clientbase import ClientBase
from beeswarm.drones.client.baits.shared.shell import Commands


logger = logging.getLogger(__name__)


class BeeTelnetClient(telnetlib.Telnet):
    IAC = chr(255)

    def write_human(self, buffer_):
        """ Emulates human typing speed """

        if self.IAC in buffer_:
            buffer_ = buffer_.replace(self.IAC, self.IAC + self.IAC)
        self.msg("send %r", buffer_)
        for char in buffer_:
            delta = random.gauss(80, 20)
            self.sock.sendall(char)
            time.sleep(delta / 1000.0)  # Convert milliseconds to seconds


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
        """
            Initialize the SSH Bee, and the Base classes.

        :param sessions: A dict which is updated every time a new session is created.
        :param options: A dict containing all options
        """
        ClientBase.__init__(self, sessions, options)
        Commands.__init__(self)
        self.client = None

    def start(self):
        """
            Launches a new Telnet client session on the server taken from the `self.options` dict.

        :param my_ip: IP of this Client itself
        """

        login = self.options['username']
        password = self.options['password']
        server_host = self.options['server']
        server_port = self.options['port']
        honeypot_id = self.options['honeypot_id']
        command_limit = random.randint(6, 11)

        session = self.create_session(server_host, server_port, honeypot_id)
        self.sessions[session.id] = session
        logger.debug(
            'Sending telnet bait session to {0}:{1}. (bait id: {2})'.format(server_host, server_port, session.id))

        try:
            self.connect()
            self.login(login, password)

            session.add_auth_attempt('plaintext', True, username=login, password=password)

            session.did_connect = True
            session.source_port = self.client.sock.getsockname()[1]
            session.did_login = True
        except InvalidLogin:
            logger.debug('Telnet session could not login. ({0})'.format(session.id))
            session.did_login = False
        except Exception as err:
            logger.debug('Caught exception: {0} {1}'.format(err, str(err), exc_info=True))
        else:
            command_count = 0
            while command_count < command_limit:
                command_count += 1
                self.sense()
                comm, param = self.decide()
                self.act(comm, param)
                time.sleep(10)
            self.act('logout')
            session.did_complete = True
        finally:
            session.alldone = True

    def connect(self):
        """
            Open a new telnet session on the remote server.
        """
        self.client = BeeTelnetClient(self.options['server'], self.options['port'])
        self.client.set_option_negotiation_callback(self.process_options)

    def login(self, login, password):
        """
            Login to the remote telnet server.

        :param login: Username to use for logging in
        :param password: Password to use for logging in
        :raise: `InvalidLogin` on failed login
        """
        self.client.read_until('Username: ')
        self.client.write(login + '\r\n')
        self.client.read_until('Password: ')
        self.client.write(password + '\r\n')
        current_data = self.client.read_until('$ ', 10)
        if not current_data.endswith('$ '):
            raise InvalidLogin

    def logout(self):
        """
            Logout from the remote server.
        """
        self.client.write('exit\r\n')
        self.client.read_all()
        self.client.close()

    def get_response(self):
        response = self.client.read_until('$ ', 5)
        return response

    def send_command(self, cmd):
        logger.debug('Sending {0} command.'.format(cmd))
        self.client.write_human(cmd + '\r\n')

    def process_options(self, *args):
        """Dummy callback, used to disable options negotiations"""


class InvalidLogin(Exception):
    pass
