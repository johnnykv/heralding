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

from heralding.capabilities.handlerbase import HandlerBase

logger = logging.getLogger(__name__)

TERMINATOR = '\r\n'


class FtpHandler(object):
    """Handles a single FTP connection"""

    def __init__(self, conn, session, options):
        self.banner = options['protocol_specific_data']['banner']
        self.max_logins = int(options['protocol_specific_data']['max_attempts'])
        self.syst_type = options['protocol_specific_data']['syst_type']
        self.authenticated = False
        self.conn = conn
        self.serve_flag = True
        self.session = session
        self.respond('200 ' + self.banner)

        # TODO: What is this?
        self.local_ip = '127.0.0.1'

        self.state = None
        self.user = None

        self.serve()

    def getcmd(self):
        return self.conn.recv(512)

    def serve(self):
        while self.serve_flag:
            resp = self.getcmd()
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
        self.user = arg
        self.respond('331 Now specify the Password.')

    def do_PASS(self, arg):
        if self.state != 'USER':
            self.respond('503 Login with USER first.')
            return
        passwd = arg
        self.session.add_auth_attempt('plaintext', username=self.user, password=passwd)
        self.respond('530 Authentication Failed.')
        if self.session.get_number_of_login_attempts() >= self.max_logins:
            self.stop()

    def do_SYST(self, arg):
        self.respond('215 %s' % self.syst_type)

    def do_QUIT(self, arg):
        self.respond('221 Bye.')
        self.serve_flag = False
        self.stop()

    def respond(self, msg):
        msg += TERMINATOR
        self.conn.send(msg)

    def stop(self):
        self.session.end_session()


class ftp(HandlerBase):
    def __init__(self, options):
        super(ftp, self).__init__(options)
        self._options = options

    def execute_capability(self, address, socket, session):
        FtpHandler(socket, session, self._options)
