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

from hive.models.session import Session
from telnetsrv.green import TelnetHandler
import telnetsrv.paramiko_ssh
from telnetsrv.paramiko_ssh import SSHHandler
from paramiko import RSAKey


from handlerbase import HandlerBase

logger = logging.getLogger(__name__)

class ssh(HandlerBase, SSHHandler):
    WELCOME = '...'
    telnet_handler = TelnetHandler

    #black voodoo to facilitate parents with different __init__ params
    def __init__(self, *args, **kwargs):
        logging.getLogger("telnetsrv.paramiko_ssh ").setLevel(logging.WARNING)
        logging.getLogger("paramiko").setLevel(logging.WARNING)
        ssh.host_key = RSAKey(filename='server.key')

        if len(args) == 2:
            #this is the constructor call for HandlerBase
            sessions = args[0]
            ssh.sessions = sessions
            ssh.port = args[1]
            super(ssh, self).__init__(sessions, ssh.port)
        elif len(args) == 3:
            request = args[0]
            client_address = args[1]
            server = args[2]
            #this session is unique for each connection
            self.session = self.create_session(client_address)
            self.auth_count = 0
            SSHHandler.__init__(self, request, client_address, server)

    def authCallbackUsername(self, username):
        #make sure no one can logon
        raise

    def authCallback(self, username, password):
        self.session.activity()
        self.session.try_login(username, password)
        raise

    def handle_session(self, gsocket, address):
            ssh._handle(gsocket, address)

    def finish(self):
        self.session.is_connected = False

    @classmethod
    def _handle(c, gsocket, address):
        ssh.streamserver_handle(gsocket, address)
