# Copyright (C) 2013 Johnny Vestergaard <jkv@unixcluster.dk>
#
# Rewritten by Aniket Panse <contact@aniketpanse.in>
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

# Aniket Panse <contact@aniketpanse.in> grants Johnny Vestergaard <jkv@unixcluster.dk>
# a perpetual, worldwide, non-exclusive, no-charge, royalty-free, irrevocable
# copyright license to reproduce, prepare derivative works of, publicly
# display, publicly perform, sublicense, relicense, and distribute [the] Contributions
# and such derivative works.


import logging
import os

from fs.path import dirname
from gevent import socket

from heralding.capabilities.handlerbase import HandlerBase

logger = logging.getLogger(__name__)

TERMINATOR = '\r\n'


class BeeFTPHandler(object):
    """Handles a single FTP connection"""

    def __init__(self, conn, session, vfs, options):
        self.banner = options['protocol_specific_data']['banner']
        self.max_logins = int(options['protocol_specific_data']['max_attempts'])
        self.syst_type = options['protocol_specific_data']['syst_type']
        self.authenticated = False
        self.conn = conn
        self.serve_flag = True
        self.session = session
        self.respond('200 ' + self.banner)
        self.vfs = vfs
        self.local_ip = '127.0.0.1'

        # These are set and used if the user is authenticated.
        self.state = None
        self.mode = None
        self.transfer_mode = None
        self.client_sock = None
        self.serv_sock = None

        self.client_addr = None  # data connection
        self.client_port = None  #
        self.working_dir = None
        self.user = None
        self.cli_ip = None
        self.cli_port = None
        self.serve()

    def serve(self):
        while self.serve_flag:
            resp = self.getcmd()
            self.session.transcript_outgoing(resp)
            if not resp:
                self.stop()
                break
            else:
                try:
                    cmd, args = resp.split(' ', 1)
                except ValueError:
                    cmd = resp
                    args = None
                else:
                    args = args.strip('\r\n')
                cmd = cmd.strip('\r\n')
                cmd = cmd.upper()
                # List of commands allowed before a login
                unauth_cmds = ['USER', 'PASS', 'QUIT', 'SYST']
                meth = getattr(self, 'do_' + cmd, None)
                if not meth:
                    self.respond('500 Unknown Command.')
                else:
                    if not self.authenticated:
                        if cmd not in unauth_cmds:
                            self.respond('503 Login with USER first.')
                            continue
                    meth(args)
                    self.state = cmd

    def do_USER(self, arg):
        if self.authenticated:
            self.respond('530 Cannot switch to another user.')
            return
        self.user = arg
        self.respond('331 Now specify the Password.')

    def do_PASS(self, arg):
        if self.state != 'USER':
            self.respond('503 Login with USER first.')
            return
        passwd = arg
        if self.session.try_auth('plaintext', username=self.user, password=passwd):
            self.authenticated = True
            self.working_dir = '/'
            self.respond('230 Login Successful.')
        else:
            self.authenticated = False
            self.respond('530 Authentication Failed.')
            if self.session.get_number_of_login_attempts() >= self.max_logins:
                self.stop()

    def do_PORT(self, arg):
        if self.mode == 'PASV':
            self.client_sock.close()
            self.mode = 'PORT'
        try:
            portlist = arg.split(',')
        except ValueError:
            self.respond('501 Bad syntax for PORT.')
            return
        if len(portlist) != 6:
            self.respond('501 Bad syntax for PORT.')
            return
        self.cli_ip = '.'.join(portlist[:4])
        self.cli_port = (int(portlist[4]) << 8) + int(portlist[5])
        self.respond('200 PORT Command Successful')

    def do_LIST(self, arg):
        self.respond('150 Listing Files.')
        self.start_data_conn()

        file_names = self.vfs.listdir(self.working_dir)
        for fname in file_names:
            abspath = self.vfs.getsyspath(self.working_dir + '/' + fname)
            self.client_sock.send(path_to_ls(abspath) + '\r\n')
        self.stop_data_conn()
        self.respond('226 File listing successful.')

    def do_CWD(self, arg):
        newdir = self.working_dir[:]
        while arg.startswith('..'):
            if newdir.endswith('/'):
                newdir = newdir[:-1]
            newdir = dirname(newdir)
            arg = arg[3:]
        newdir = os.path.join(newdir, arg)
        if self.vfs.isdir(newdir):
            self.working_dir = newdir[:]
            self.respond('250 Directory Changed.')
        else:
            self.respond('550 The system cannot find the path specified.')

    def do_NOOP(self, arg):
        self.respond('200 Command Successful.')

    def do_SYST(self, arg):
        self.respond('215 %s' % self.syst_type)

    def do_QUIT(self, arg):
        self.respond('221 Bye.')
        self.serve_flag = False
        self.stop()

    def respond(self, msg):
        msg += TERMINATOR
        self.session.transcript_outgoing(msg)
        self.conn.send(msg)

    def stop(self):
        self.session.end_session()


class ftp(HandlerBase):
    def __init__(self, options, work_dir):
        super(ftp, self).__init__(options, work_dir)
        self._options = options

    def handle_session(self, gsocket, address):
        session = self.create_session(address)
        try:
            BeeFTPHandler(gsocket, session, self.vfsystem.opendir('/pub/ftp'), self._options)
        finally:
            self.close_session(session)