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

import ftplib
import random
import logging
from datetime import datetime
import gevent
from gevent import socket
from ftplib import FTP

from beeswarm.drones.client.baits.clientbase import ClientBase


logger = logging.getLogger(__name__)


class ftp(ClientBase):
    COMMAND_MAP = {
        'pwd': ['list'],
        'list': ['retrieve', 'cwd'],
        'cwd': ['list', 'retrieve', 'pwd'],
        'retrieve': ['list', 'quit']
    }

    def __init__(self, sessions, options):
        """
            Initializes common values.

        :param sessions: A dict which is updated every time a new session is created.
        :param options: A dict containing all options
        """
        super(ftp, self).__init__(sessions, options)

        self.state = {
            'current_dir': '/',
            'file_list': [],
            'dir_list': [],
            'last_command': 'pwd'  # Assume that client has previously performed a pwd (to avoid IndexErrors)
        }
        self.client = FTP()
        self.senses = ['pwd', 'list']
        self.actions = ['cwd', 'retrieve']

    def start(self):

        """
            Launches a new FTP client session on the server taken from the `self.options` dict.

        :param my_ip: IP of this Client itself
        """
        username = self.options['username']
        password = self.options['password']
        server_host = self.options['server']
        server_port = self.options['port']
        honeypot_id = self.options['honeypot_id']
        command_limit = random.randint(6, 11)

        session = self.create_session(server_host, server_port, honeypot_id)

        self.sessions[session.id] = session
        logger.debug(
            'Sending {0} bait session to {1}:{2}. (bait id: {3})'.format('ftp', server_host, server_port, session.id))

        self.file_list = []
        try:
            self.connect()
            session.did_connect = True

            # TODO: Catch login failure
            self.login(username, password)
            session.add_auth_attempt('plaintext', True, username=username, password=password)

            session.did_login = True
            session.timestamp = datetime.utcnow()
        except ftplib.error_perm as err:
            logger.debug('Caught exception: {0} ({1})'.format(err, str(type(err))))
        except socket.error as err:
            logger.debug('Error while communicating: {0} ({1})'.format(err, str(type(err))))
        else:
            command_count = 0
            while command_count <= command_limit:
                command_count += 1
                try:
                    self.sense()
                    cmd, param = self.decide()
                    self.act(cmd, param)
                    gevent.sleep(random.uniform(0, 3))
                except IndexError:  # This means we hit an empty folder, or a folder with only files.
                    continue
            session.did_complete = True
        finally:
            if self.client.sock is not None:
                self.client.quit()
            session.alldone = True

    def sense(self):
        """
            Launches a few "sensing" commands such as 'ls', or 'pwd'
            and updates the current bait state.
        """
        cmd_name = random.choice(self.senses)
        command = getattr(self, cmd_name)
        self.state['last_command'] = cmd_name
        command()

    def decide(self):
        """
            Decides the next command to be launched based on the current state.

        :return: Tuple containing the next command name, and it's parameters.
        """
        next_command_name = random.choice(self.COMMAND_MAP[self.state['last_command']])
        param = ''
        if next_command_name == 'retrieve':
            param = random.choice(self.state['file_list'])
        elif next_command_name == 'cwd':
            param = random.choice(self.state['dir_list'])
        return next_command_name, param

    def act(self, cmd_name, param):
        """
            Run the command with the parameters.

        :param cmd_name: The name of command to run
        :param param: Params for the command
        """
        command = getattr(self, cmd_name)
        if param:
            command(param)
        else:
            command()

    def list(self):
        """
            Run the FTP LIST command, and update the state.
        """
        logger.debug('Sending FTP list command.')
        self.state['file_list'] = []
        self.state['dir_list'] = []
        self.client.retrlines('LIST', self._process_list)

    def retrieve(self, filename):
        """
            Run the FTP RETR command, and download the file

        :param filename: Name of the file to download
        """
        logger.debug('Sending FTP retr command. Filename: {}'.format(filename))
        self.client.retrbinary('RETR {}'.format(filename), self._save_file)

    def pwd(self):
        """
            Send the FTP PWD command.
        """
        logger.debug('Sending FTP pwd command.')
        self.state['current_dir'] = self.client.pwd()

    def cwd(self, newdir):
        """
            Send the FTP CWD command

        :param newdir: Directory to change to
        """
        logger.debug('Sending FTP cwd command. New Workding Directory: {}'.format(newdir))
        self.client.cwd(newdir)
        self.state['current_dir'] = self.client.pwd()

    def quit(self):
        """
            End the current FTP session.
        """
        logger.debug('Sending FTP quit command.')
        self.client.quit()

    def login(self, username, password):
        """
            Login to the remote server

        :param username: The username to use for login
        :param password: The password to use for login
        """
        self.client.login(username, password)

    def _process_list(self, list_line):
        # -rw-r--r-- 1 ftp ftp 68	 May 09 19:37 testftp.txt
        """
            Processes a line of 'ls -l' output, and updates state accordingly.

        :param list_line: Line to process
        """
        res = list_line.split(' ', 8)
        if res[0].startswith('-'):
            self.state['file_list'].append(res[-1])
        if res[0].startswith('d'):
            self.state['dir_list'].append(res[-1])

    def _save_file(self, data):
        """ Dummy function since FTP.retrbinary() needs a callback """

    def connect(self):
        """
            Connect to the remote FTP server (Honeypot).
        """
        self.client.connect(self.options['server'], self.options['port'])
