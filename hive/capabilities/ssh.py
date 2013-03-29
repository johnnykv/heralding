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

from telnetsrv.green import TelnetHandler
from telnetsrv.paramiko_ssh import SSHHandler
from paramiko import RSAKey

from handlerbase import HandlerBase

logger = logging.getLogger(__name__)


class ssh(HandlerBase):
    def __init__(self, sessions, options):
        logging.getLogger("telnetsrv.paramiko_ssh ").setLevel(logging.WARNING)
        logging.getLogger("paramiko").setLevel(logging.WARNING)
        super(ssh, self).__init__(sessions, options)

    def handle_session(self, gsocket, address):
        session = self.create_session(address, gsocket)
        ssh_wrapper(address, None, gsocket, session, self.options)


class ssh_wrapper(SSHHandler):
    """
    Wraps the telnetsrv paramiko module to fit the Hive architecture.
    """

    WELCOME = '...'
    telnet_handler = TelnetHandler

    def __init__(self, client_address, server, socket, session, options):
        self.session = session
        self.auth_count = 0
        server_key = options['key']
        ssh_wrapper.host_key = RSAKey(filename=server_key)
        request = ssh_wrapper.dummy_request()
        request._sock = socket
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
        self.session.connected = False