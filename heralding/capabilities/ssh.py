import os
import sys
import logging
import functools

from heralding.capabilities.handlerbase import HandlerBase

import asyncssh
from Crypto.PublicKey import RSA

logger = logging.getLogger(__name__)


def change_server_banner(banner):

    @functools.wraps(asyncssh.connection.SSHConnection._send_version)
    def send_version(self):
        """Start the SSH handshake"""

        version = bytes(banner, 'utf-8')

        if self.is_client():
            self._client_version = version
            self._extra.update(client_version=version.decode('ascii'))
        else:
            self._server_version = version
            self._extra.update(server_version=version.decode('ascii'))

        self._send(version + b'\r\n')

    asyncssh.connection.SSHConnection._send_version = send_version



class SSH(asyncssh.SSHServer, HandlerBase):
    def __init__(self, options, loop):
        asyncssh.SSHServer.__init__(self)
        HandlerBase.__init__(self, options, loop)
        banner = self.options['protocol_specific_data']['banner']
        change_server_banner(banner)

    def connection_made(self, conn):
        self.address = conn.get_extra_info('peername')
        self.handle_connection()
        logger.debug('SSH connection received from %s.' % conn.get_extra_info('peername')[0])

    def connection_lost(self, exc):
        self.close_session(self.session)
        if exc:
            logger.debug('SSH connection error: ' + str(exc), file=sys.stderr)
        else:
            logger.debug('SSH connection closed.')

    def begin_auth(self, username):
        return True

    def password_auth_supported(self):
        return True

    def validate_password(self, username, password):
        self.session.add_auth_attempt('plaintext', username=username, password=password)
        return False

    def handle_connection(self):
        if HandlerBase.global_sessions > HandlerBase.MAX_GLOBAL_SESSIONS:
            protocol = self.__class__.__name__.lower()
            logger.warning(
                'Got {0} session on port {1} from {2}:{3}, but not handling it because the global session limit has '
                'been reached'.format(protocol, self.port, *self.address))
        else:
            self.session = self.create_session(self.address)

    @staticmethod
    def generate_ssh_key(ssh_key_file):
        if not os.path.isfile(ssh_key_file):
            with open(ssh_key_file, 'w') as _file:
                rsa_key = RSA.generate(2048)
                priv_key_text = str(rsa_key.exportKey('PEM', pkcs=1), 'utf-8')
                _file.write(priv_key_text)
