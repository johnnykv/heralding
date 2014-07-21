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
import time

from paramiko import SSHClient, AutoAddPolicy, SSHException

from beeswarm.drones.client.baits.clientbase import ClientBase
from beeswarm.drones.client.baits.shared.shell import Commands
from beeswarm.errors import AuthenticationFailed


logger = logging.getLogger(__name__)


class ssh(ClientBase, Commands):
    def __init__(self, sessions, options):
        """
            Initialize the SSH Bee, and the Base classes.

        :param sessions: A dict which is updated every time a new session is created.
        :param options: A dict containing all options
        """
        ClientBase.__init__(self, sessions, options)
        Commands.__init__(self)
        self.client = SSHClient()
        self.client.set_missing_host_key_policy(AutoAddPolicy())
        self.comm_chan = None

    def start(self):
        """
            Launches a new SSH client session on the server taken from the `self.options` dict.

        :param my_ip: IP of this Client itself
        """
        username = self.options['username']
        password = self.options['password']
        server_host = self.options['server']
        server_port = self.options['port']
        honeypot_id = self.options['honeypot_id']

        session = self.create_session(server_host, server_port, honeypot_id)

        self.sessions[session.id] = session
        logger.debug(
            'Sending %s bait session to {0}:{1}. (bait id: %s)'.format('ssh', server_host, server_port, session.id))
        try:
            self.connect_login()
            # TODO: Handle failed login
            session.add_auth_attempt('plaintext', True, username=username, password=password)
            session.did_login = True
        except (SSHException, AuthenticationFailed) as err:
            logger.debug('Caught exception: {0} ({1})'.format(err, str(type(err))))
        else:
            self.sense()
            comm, param = self.decide()
            self.act(comm, param)
            time.sleep(10)
        finally:
            session.alldone = True

    def send_command(self, cmd):
        """
            Send a command to the remote SSH server.

        :param cmd: The command to send
        """
        logger.debug('Sending {0} command.'.format(cmd))
        self.comm_chan.sendall(cmd + '\n')

    def get_response(self):
        """
            Get the response from the server. *This may not return the full response*

        :return: Response data
        """
        while not self.comm_chan.recv_ready():
            time.sleep(0.5)
        return self.comm_chan.recv(2048)

    def connect_login(self):
        """
            Try to login to the Remote SSH Server.

        :return: Response text on successful login
        :raise: `AuthenticationFailed` on unsuccessful login
        """
        self.client.connect(self.options['server'], self.options['port'], self.options['username'],
                            self.options['password'])
        self.comm_chan = self.client.invoke_shell()
        time.sleep(1)  # Let the server take some time to get ready.
        while not self.comm_chan.recv_ready():
            time.sleep(0.5)
        login_response = self.comm_chan.recv(2048)
        if not login_response.endswith('$ '):
            raise AuthenticationFailed
        return login_response

    def logout(self):
        """
            Logout from the remote server
        """
        self.send_command('exit')
        self.get_response()
        self.comm_chan.close()
