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

import socket
import logging

from hive.models.session import Session
from pyftpdlib import ftpserver


from handlerbase import HandlerBase

logger = logging.getLogger(__name__)

class ftp(HandlerBase):
    port = 2121
    #port = 23
    #max_tries = 3

    def __init__(self, sessions):
        self.sessions = sessions

    def handle(self, gsocket, address):
        session = Session(address[0], address[1], 'ftp', ftp.port)
        authorizer = ftp.ftpAuthorizer(session)
        handler = ftpserver.FTPHandler
        handler.authorizer = authorizer
        handler.max_login_attempts = 3

        f = ftpserver.FTPServer(('', '0'), handler)

        ftphandler = ftpserver.FTPHandler(gsocket, f)

        #send banner to client
        ftphandler.handle()
        #start command loop, will exit on disconnect.
        f.serve_forever()

    def get_port(self):
        return ftp.port

    class ftpAuthorizer(ftpserver.DummyAuthorizer):
        def __init__(self, session):
            super(ftp.ftpAuthorizer, self).__init__()
            self.session = session

        def validate_authentication(self, username, password):
            self.session.try_login(username, password)
