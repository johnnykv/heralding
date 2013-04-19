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

from handlerbase import HandlerBase

logger = logging.getLogger(__name__)

TERMINATOR = "\r\n"


class BeeFTPHandler(object):
    """Handles a single FTP connection"""

    def __init__(self, conn, session, options):
        self.banner = options['banner']
        self.max_logins = int(options['max_attempts'])
        self.curr_logins = 0
        self.authenticated = False
        self.conn = conn
        self.session = session
        self.respond("200 " + self.banner)
        self.state = None
        self.serve()

    def serve(self):
        while True:
            resp = self.getcmd()
            if not resp:
                self.stop()
                break
            else:
                try:
                    cmd, args = resp.split(" ", 1)
                except ValueError:
                    cmd = resp
                    args = None
                cmd = cmd.upper()
                meth = getattr(self, 'do_' + cmd, None)
                if not meth:
                    self.respond("500 Unknown Command.")
                else:
                    meth(args)
                    self.state = cmd

    def do_USER(self, arg):
        if self.authenticated:
            self.respond("530 Cannot switch to another user.")
            return
        self.user = arg
        self.respond("331 Now specify the Password.")
        return

    def do_PASS(self, arg):
        if self.state != 'USER':
            self.respond("503 Login with USER first.")
            return
        self.curr_logins += 1
        self.passwd = arg
        self.session.try_login(self.user, self.passwd)
        self.respond("530 Authentication Failed.")
        if self.curr_logins >= self.max_logins:
            self.stop()
        return

    def getcmd(self):
        return self.conn.recv(512)

    def respond(self, msg):
        msg += TERMINATOR
        self.conn.send(msg)

    def stop(self):
        self.conn.close()


class ftp(HandlerBase):

    def __init__(self, sessions, options):
        super(ftp, self).__init__(sessions, options)
        self._options = options

    def handle_session(self, gsocket, address):
        session = self.create_session(address, gsocket)
        BeeFTPHandler(gsocket, session, self._options)
