# Copyright (C) 2013 Johnny Vestergaard <jkv@unixcluster.dk>
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
import curses

import logging
import os
import random
import socket
from fs.path import dirname

from telnetsrv.green import TelnetHandler, command

from beeswarm.hive.capabilities.handlerbase import HandlerBase
from beeswarm.hive.helpers.common import path_to_ls

logger = logging.getLogger(__name__)


class telnet(HandlerBase):
    def __init__(self, sessions, options, users, work_dir):
        super(telnet, self).__init__(sessions, options, users, work_dir)

    def handle_session(self, gsocket, address):
        telnet_wrapper.max_tries = int(self.options['max_attempts'])
        session = self.create_session(address, gsocket)
        try:
            telnet_wrapper(address, None, gsocket, session, self.vfsystem)
        except socket.error as err:
            logger.debug('Unexpected end of telnet session: {0}, errno: {1}. ({2})'.format(err, err.errno, session.id))

        session.connected = False


class telnet_wrapper(TelnetHandler):
    """
    Wraps the telnetsrv module to fit the Hive architecture.
    """
    max_tries = 3
    PROMPT = ''
    WELCOME = 'Logged in.'
    HOSTNAME = 'host'
    authNeedUser = True
    authNeedPass = True
    TERM = 'ansi'

    # Making these empty will disable option negotiations, so less headache for us.
    DOACK = {}
    WILLACK = {}

    def __init__(self, client_address, server, socket, session, vfs):
        self.session = session
        self.auth_count = 0
        request = telnet_wrapper.false_request()
        request._sock = socket

        self.vfs = vfs
        self.working_dir = None
        self.total_file_size = str(random.randint(588, 22870))
        TelnetHandler.__init__(self, request, client_address, server)

    def authCallback(self, username, password):
        while self.auth_count < telnet_wrapper.max_tries:
            if self.session.try_auth(type='plaintext', username=username, password=password):
                self.working_dir = '/'
                self.username = username
                self.PROMPT = '[{0}@{1} {2}]$ '.format(self.username, self.HOSTNAME, self.working_dir)
                return True
            self.writeline('Invalid username/password')
            self.auth_count += 1
            self.authentication_ok()
        return False

    @command('ls')
    def command_ls(self, params):
        self.writeline('total ' + self.total_file_size)  # report a fake random file size
        file_names = self.vfs.listdir(self.working_dir)
        for fname in file_names:
            abspath = self.vfs.getsyspath(self.working_dir + '/' + fname)
            self.writeline(path_to_ls(abspath))

    @command('echo')
    def command_echo(self, params):
        if not params:
            self.writeline('')
            return
        elif '*' in params:
            params.remove('*')
            params.extend(self.vfs.listdir())
        self.writeline(' '.join(params))

    @command('cd')
    def command_cd(self, params):
        newdir = self.working_dir[:]
        if len(params) > 1:
            self.writeline('cd: string not in pwd: {0}'.format(params[0]))
            return
        arg = params[0]
        while arg.startswith('..'):
            if newdir.endswith('/'):
                newdir = newdir[:-1]
            newdir = dirname(newdir)
            arg = arg[3:]
        newdir = os.path.join(newdir, arg)
        if self.vfs.isdir(newdir):
            self.working_dir = newdir[:]
            self.PROMPT = '[{0}@{1} {2}]$ '.format(self.username, self.HOSTNAME, self.working_dir)
        else:
            self.writeline('cd: no such file or directory: {0}'.format(params[0]))

    def session_end(self):
        self.session.connected = False

    def setterm(self, term):

        # Dummy file for the purpose of tests.
        f = open('/dev/null', 'w')
        curses.setupterm(term, f.fileno())  # This will raise if the termtype is not supported
        self.TERM = term
        self.ESCSEQ = {}
        for k in self.KEYS.keys():
            str = curses.tigetstr(curses.has_key._capability_names[k])
            if str:
                self.ESCSEQ[str] = k
        self.CODES['DEOL'] = curses.tigetstr('el')
        self.CODES['DEL'] = curses.tigetstr('dch1')
        self.CODES['INS'] = curses.tigetstr('ich1')
        self.CODES['CSRLEFT'] = curses.tigetstr('cub1')
        self.CODES['CSRRIGHT'] = curses.tigetstr('cuf1')
