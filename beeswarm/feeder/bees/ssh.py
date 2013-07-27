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
from paramiko import SSHClient, AutoAddPolicy, SSHException
import time

from beeswarm.feeder.bees.clientbase import ClientBase
from beeswarm.feeder.bees.shared.shell import Commands
from beeswarm.hive.capabilities.telnet import AuthenticationFailed


class ssh(ClientBase, Commands):

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
        super(ssh, self).__init__(sessions, options)
        self.client = None
        self.comm_chan = None
        self.state = {
            'last_command': 'echo',
            'working_dir': '/',
            'file_list': [],
            'dir_list': [],
        }
        self.command_count = 0
        self.command_limit = random.randint(6, 11)

    def do_session(self, my_ip):
        login = self.options['login']
        password = self.options['password']
        server_host = self.options['server']
        server_port = self.options['port']
        session = self.create_session(login, password, server_host, server_port, my_ip)

        self.sessions[session.id] = session
        logging.debug(
            'Sending %s honeybee to %s:%s. (bee id: %s)' % ('ssh', server_host, server_port, session.id))
        self.client = SSHClient()
        self.client.set_missing_host_key_policy(AutoAddPolicy())
        try:
            self.client.connect(server_host, server_port, login, password)
            self.comm_chan = self.client.invoke_shell()
            time.sleep(1)
            while not self.comm_chan.recv_ready():
                time.sleep(0.5)
            login_response = self.comm_chan.recv(2048)
            if not login_response.endswith('$ '):
                raise AuthenticationFailed
            session.did_login = True
        except SSHException as err:
            logging.debug('Caught exception: %s (%s)' % (err, str(type(err))))
        else:
            # Run some commands
            pass
        finally:
            session.alldone = True

    def send_command(self, cmd):
        logging.debug('Sending %s command.' % cmd)
        self.comm_chan.sendall(cmd + '\n')

    def get_response(self):
        while not self.comm_chan.recv_ready():
            time.sleep(0.5)
        return self.comm_chan.recv(2048)