# pylint: disable-msg=E1101
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

from telnetsrv.paramiko_ssh import SSHHandler, TelnetToPtyHandler
from paramiko import RSAKey
from paramiko.ssh_exception import SSHException

from beeswarm.drones.honeypot.capabilities.handlerbase import HandlerBase
from beeswarm.drones.honeypot.capabilities.shared.shell import Commands

logger = logging.getLogger(__name__)


class SSH(HandlerBase):
    def __init__(self, sessions, options, work_dir, key='server.key'):
        logging.getLogger("telnetsrv.paramiko_ssh ").setLevel(logging.WARNING)
        logging.getLogger("paramiko").setLevel(logging.WARNING)
        self.key = key
        super(SSH, self).__init__(sessions, options, work_dir)

    def handle_session(self, gsocket, address):
        session = self.create_session(address, gsocket)
        try:
            SshWrapper(address, None, gsocket, session, self.options, self.vfsystem, self.key)
        except (SSHException, EOFError) as ex:
            logger.debug('Unexpected end of ssh session: {0}. ({1})'.format(ex, session.id))

        session.connected = False


class BeeTelnetHandler(Commands):
    def __init__(self, request, client_address, server, vfs, session):
        Commands.__init__(self, request, client_address, server, vfs, session)


class SshWrapper(SSHHandler):
    """
    Wraps the telnetsrv paramiko module to fit the Honeypot architecture.
    """

    WELCOME = '...'
    HOSTNAME = 'host'
    PROMPT = None
    telnet_handler = BeeTelnetHandler

    def __init__(self, client_address, server, socket, session, options, vfs, key):
        self.session = session
        self.auth_count = 0
        self.vfs = vfs
        self.working_dir = None
        self.username = None

        SshWrapper.host_key = RSAKey(filename=key)
        request = SshWrapper.dummy_request()
        request._sock = socket

        SSHHandler.__init__(self, request, client_address, server)

        class __MixedPtyHandler(TelnetToPtyHandler, BeeTelnetHandler):
            # BaseRequestHandler does not inherit from object, must call the __init__ directly
            def __init__(self, *args):
                TelnetToPtyHandler.__init__(self, *args)

        self.pty_handler = __MixedPtyHandler

    def authCallbackUsername(self, username):
        # make sure no one can logon
        raise

    def authCallback(self, username, password):
        self.session.activity()
        if self.session.try_auth('plaintext', username=username, password=password):
            self.working_dir = '/'
            self.username = username
            self.telnet_handler.PROMPT = '[{0}@{1} {2}]$ '.format(self.username, self.HOSTNAME, self.working_dir)
            return True
        raise

    def finish(self):
        self.session.connected = False

    def setup(self):

        self.transport.load_server_moduli()

        self.transport.add_server_key(self.host_key)

        self.transport.start_server(server=self)

        while True:
            channel = self.transport.accept(20)
            if channel is None:
                # check to see if any thread is running
                any_running = False
                for _, thread in self.channels.items():
                    if thread.is_alive():
                        any_running = True
                        break
                if not any_running:
                    break

    def start_pty_request(self, channel, term, modes):
        """Start a PTY - intended to run it a (green)thread."""
        request = self.dummy_request()
        request._sock = channel
        request.modes = modes
        request.term = term
        request.username = self.username

        # This should block until the user quits the pty
        self.pty_handler(request, self.client_address, self.tcp_server, self.vfs, self.session)

        # Shutdown the entire session
        self.transport.close()
