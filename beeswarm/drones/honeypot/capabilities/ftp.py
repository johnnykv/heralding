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

import logging
import os

from gevent import socket
from fs.path import dirname

from beeswarm.drones.honeypot.capabilities.handlerbase import HandlerBase
from beeswarm.drones.honeypot.helpers.common import send_whole_file, path_to_ls


logger = logging.getLogger(__name__)

TERMINATOR = '\r\n'


class BeeFTPHandler(object):
    """Handles a single FTP connection"""

    def __init__(self, conn, session, vfs, options):
        self.banner = options['protocol_specific_data']['banner']
        self.max_logins = int(options['protocol_specific_data']['max_attempts'])
        self.syst_type = options['protocol_specific_data']['syst_type']
        self.curr_logins = 0
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
        self.curr_logins += 1
        self.passwd = arg
        if self.session.try_auth('plaintext', username=self.user, password=self.passwd):
            self.authenticated = True
            self.working_dir = '/'
            self.respond('230 Login Successful.')
        else:
            self.authenticated = False
            self.respond('530 Authentication Failed.')
            if self.curr_logins >= self.max_logins:
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

    def do_PWD(self, arg):
        self.respond('257 "%s"' % self.working_dir)

    def do_PASV(self, arg):
        self.mode = 'PASV'
        self.serv_sock = socket.socket()
        self.serv_sock.bind((self.local_ip, 0))
        self.serv_sock.listen(1)
        ip, port = self.serv_sock.getsockname()
        self.respond('227 Entering Passive Mode (%s,%u,%u).' % (','.join(ip.split('.')),
                                                                port >> 8 & 0xFF, port & 0xFF))

    def do_NOOP(self, arg):
        self.respond('200 Command Successful.')

    def do_SYST(self, arg):
        self.respond('215 %s' % self.syst_type)

    def do_QUIT(self, arg):
        self.respond('221 Bye.')
        self.serve_flag = False
        self.stop()

    def do_RETR(self, arg):
        filename = os.path.join(self.working_dir, arg)
        if self.vfs.isfile(filename):
            self.respond('150 Initiating transfer.')
            self.start_data_conn()
            file_ = self.vfs.open(filename)
            send_whole_file(self.client_sock.fileno(), file_.fileno())
            file_.close()
            self.stop_data_conn()
            self.respond('226 Transfer complete.')
        else:
            self.respond('550 The system cannot find the file specified.')

    def do_TYPE(self, arg):
        self.transfer_mode = arg
        self.respond('200 Transfer type set to:' + self.transfer_mode)

    def getcmd(self):
        return self.conn.recv(512)

    def start_data_conn(self):
        if self.mode == 'PASV':
            self.client_sock, (self.cli_ip, self.cli_port) = self.serv_sock.accept()
        else:
            self.client_sock = socket.socket()
            self.client_sock.connect((self.cli_ip, self.cli_port))

    def stop_data_conn(self):
        self.client_sock.close()
        if self.mode == 'PASV':
            self.serv_sock.close()

    def respond(self, msg):
        msg += TERMINATOR
        self.session.transcript_outgoing(msg)
        self.conn.send(msg)

    def stop(self):
        self.conn.close()
        self.session.connected = False


class ftp(HandlerBase):
    def __init__(self, sessions, options, work_dir):
        super(ftp, self).__init__(sessions, options, work_dir)
        self._options = options

    def handle_session(self, gsocket, address):
        session = self.create_session(address, gsocket)
        BeeFTPHandler(gsocket, session, self.vfsystem.opendir('/pub/ftp'), self._options)