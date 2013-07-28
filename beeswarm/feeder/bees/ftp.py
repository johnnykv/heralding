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
import ftplib
import pprint
import random
from datetime import datetime

from ftplib import FTP
from beeswarm.feeder.bees.clientbase import ClientBase


class ftp(ClientBase):

    COMMAND_MAP = {
        'pwd': ['list'],
        'list': ['retrieve', 'cwd'],
        'cwd': ['list', 'retrieve', 'pwd'],
        'retrieve': ['list', 'quit']
    }

    def __init__(self, sessions, options):
        super(ftp, self).__init__(sessions, options)
        self.state = {
            'current_dir': '/',
            'file_list': [],
            'dir_list': [],
            'last_command': 'pwd'  # Assume that client has previously performed a pwd (to avoid IndexErrors)
        }
        self.senses = ['pwd', 'list']
        self.actions = ['cwd', 'retrieve']
        self.client = FTP()
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
            'Sending %s honeybee to %s:%s. (bee id: %s)' % ('ftp', server_host, server_port, session.id))

        self.file_list = []
        try:
            self.connect()
            session.did_connect = True
            self.login(login, password)
            session.did_login = True
            session.timestamp = datetime.utcnow()
        except ftplib.error_perm as err:
            logging.debug('Caught exception: %s (%s)' % (err, str(type(err))))
        else:
            while self.command_count <= self.command_limit:
                self.command_count += 1
                try:
                    self.sense()
                    cmd, param = self.decide()
                    self.act(cmd, param)
                except IndexError:  # This means we hit an empty folder, or a folder with only files.
                    continue
            session.did_complete = True
        finally:
            self.client.quit()
            session.alldone = True

    def sense(self):
        cmd_name = random.choice(self.senses)
        command = getattr(self, cmd_name)
        self.state['last_command'] = cmd_name
        command()

    def decide(self):
        next_command_name = random.choice(self.COMMAND_MAP[self.state['last_command']])
        param = ''
        if next_command_name == 'retrieve':
            param = random.choice(self.state['file_list'])
        elif next_command_name == 'cwd':
            param = random.choice(self.state['dir_list'])
        return next_command_name, param

    def act(self, cmd_name, param):
        command = getattr(self, cmd_name)
        if param:
            command(param)
        else:
            command()

    def list(self):
        logging.debug('Sending FTP list command.')
        self.state['file_list'] = []
        self.state['dir_list'] = []
        self.client.retrlines('LIST', self._process_list)

    def retrieve(self, filename):
        logging.debug('Sending FTP retr command. Filename: {}'.format(filename))
        self.client.retrbinary('RETR {}'.format(filename), self._save_file)

    def pwd(self):
        logging.debug('Sending FTP pwd command.')
        self.state['current_dir'] = self.client.pwd()

    def cwd(self, newdir):
        logging.debug('Sending FTP cwd command. New Workding Directory: {}'.format(newdir))
        self.client.cwd(newdir)
        self.state['current_dir'] = self.client.pwd()

    def quit(self):
        logging.debug('Sending FTP quit command.')
        self.client.quit()

    def connect(self):
        self.client.connect(self.options['server'], self.options['port'])

    def login(self, username, password):
        self.client.login(username, password)

    def _process_list(self, list_line):
        # -rw-r--r-- 1 ftp ftp 68	 May 09 19:37 testftp.txt
        res = list_line.split(' ', 8)
        if res[0].startswith('-'):
            self.state['file_list'].append(res[-1])
        if res[0].startswith('d'):
            self.state['dir_list'].append(res[-1])

    def _save_file(self, data):
        """ Dummy function since FTP.retrbinary() needs a callback """

