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

import logging
import asyncore

from hive.models.session import Session
from pyftpdlib import ftpserver

from handlerbase import HandlerBase

logger = logging.getLogger(__name__)


class ftp(HandlerBase):

    def __init__(self, sessions, port):
        super(ftp, self).__init__(sessions, port)

    def handle_session(self, gsocket, address):

        session = self.create_session(address)

        f = ftp.BeeSwarmFTPServer(('', 0), ftpserver.FTPHandler)
        ftphandler = ftpserver.FTPHandler(gsocket, f)
        ftphandler.authorizer = ftp.ftpAuthorizer(session)
        #TODO: configurable
        ftphandler.banner = "220 Microsoft FTP Service"

        #Send '200' status and banner
        ftphandler.handle()
        #start command loop, will exit on disconnect.
        f.serve_forever()
        f.close_all()
        session.is_connected = False

    class ftpAuthorizer(ftpserver.DummyAuthorizer):
        def __init__(self, session):
            super(ftp.ftpAuthorizer, self).__init__()
            self.session = session

        def validate_authentication(self, username, password):
            self.session.try_login(username, password)

    class BeeSwarmFTPServer(ftpserver.FTPServer):

        @classmethod
        def serve_forever(cls, timeout=1.0, use_poll=False, count=None):

            from pyftpdlib.ftpserver import _scheduler

            poll_fun = asyncore.poll

            try:
                while len(asyncore.socket_map) > 1:
                    poll_fun(timeout)
                    _scheduler()
            except (KeyboardInterrupt, SystemExit, asyncore.ExitNow):
                pass
            finally:
                cls.close_all()

