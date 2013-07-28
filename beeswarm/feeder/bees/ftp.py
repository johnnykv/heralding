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
import random
from datetime import datetime

from ftplib import FTP
from beeswarm.feeder.bees.clientbase import ClientBase


class ftp(ClientBase):

    def __init__(self, sessions, options):
        super(ftp, self).__init__(sessions, options)
        self.state = {
            'current_dir': '/',
            'file_list': [],
            'dir_list': []
        }
        self.senses = ['pwd', 'list']
        self.actions = ['cd', 'retrieve']
        self.client = FTP()

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
            session.did_complete = True
        except ftplib.error_perm as err:
            logging.debug('Caught exception: %s (%s)' % (err, str(type(err))))
        finally:
            self.client.quit()
            session.alldone = True

    def list(self):
        self.client.retrlines('LIST', self._process_list)

    def retrieve(self, filename):
        self.client.retrbinary(filename, self._save_file)

    def pwd(self):
        self.state['current_dir'] = self.client.pwd()

    def cwd(self, newdir):
        self.client.cwd(newdir)
        self.state['current_dir'] = self.client.pwd()

    def connect(self):
        self.client.connect(self.options['server'], self.options['port'])

    def login(self, username, password):
        self.client.login(username, password)

    def _process_list(self, list_line):
        # -rw-r--r-- 1 ftp ftp 68	 May 09 19:37 testftp.txt
        res = list_line.split(' ', 8)
        if res[0].startswith('-'):
            self.state['file_list'].append(res[-1])
        elif res[0].startswith('d'):
            self.state['dir_list'].append(res[-1])

    def _save_file(self, data):
        """ Dummy function since FTP.retrbinary() needs a callback """

