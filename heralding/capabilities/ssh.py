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
import os.path

from Crypto.PublicKey import RSA
from paramiko import RSAKey
from paramiko.ssh_exception import SSHException
from telnetsrv.paramiko_ssh import SSHHandler

from heralding.capabilities.handlerbase import HandlerBase
from heralding.capabilities.shared.shell import Commands

logger = logging.getLogger(__name__)


class SSH(HandlerBase):
    def __init__(self, options):
        logging.getLogger("telnetsrv.paramiko_ssh ").setLevel(logging.WARNING)
        logging.getLogger("paramiko").setLevel(logging.WARNING)

        # generate key
        ssh_key_file = 'ssh.key'
        if not os.path.isfile(ssh_key_file):
            with open(ssh_key_file, 'w') as _file:
                rsa_key = RSA.generate(1024)
                priv_key_text = rsa_key.exportKey('PEM', pkcs=1)
                _file.write(priv_key_text)
                _file.close()
        self.key = RSAKey(filename=ssh_key_file)
        super(SSH, self).__init__(options)

    def execute_capability(self, address, socket, session):
        SshWrapper(address, None, socket, session, self.options, self.key)


class BeeTelnetHandler(Commands):
    def __init__(self, request, client_address, server, session):
        Commands.__init__(self, request, client_address, server, session)


class SshWrapper(SSHHandler):
    # reusing telnetsrv stuff
    telnet_handler = BeeTelnetHandler

    def __init__(self, client_address, server, socket, session, options, key):
        self.session = session
        self.auth_count = 0
        self.working_dir = None
        self.username = None
        self.banner = 'SSH-2.0-OpenSSH_6.6.1p1 Ubuntu-2ubuntu2.8'
        if 'protocol_specific_data' in options and 'banner' in options['protocol_specific_data']:
            self.banner = options['protocol_specific_data']['banner']

        SshWrapper.host_key = key
        # TODO: Figure out why this is necessary
        request = SshWrapper.dummy_request()
        request._sock = socket
        # TODO END

        SSHHandler.__init__(self, request, client_address, server)

    def authCallbackUsername(self, username):
        # make sure no one can logon
        raise

    def authCallback(self, username, password):
        self.session.activity()
        self.session.add_auth_attempt('plaintext', username=username, password=password)
        raise

    def finish(self):
        self.session.end_session()

    def setup(self):

        self.transport.load_server_moduli()

        self.transport.add_server_key(self.host_key)

        self.transport.local_version = self.banner

        try:
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
        except SSHException as exception:
            logger.warning('Premature end of SSH session: {0} ({1})'.format(exception, self.session.id))
