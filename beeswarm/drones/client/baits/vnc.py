# Copyright (C) 2013 Aniket Panse <contact@aniketpanse.in>
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
# display, publicly perform, sublicense, and distribute [the] Contributions
# and such derivative works.

import logging
import socket

from beeswarm.drones.client.baits.clientbase import ClientBase
from beeswarm.shared.vnc_constants import *
from beeswarm.shared.misc.rfbes import RFBDes


logger = logging.getLogger(__name__)


class Vnc(ClientBase):
    def __init__(self, options):
        super(Vnc, self).__init__(options)

    def start(self):
        """
            Launches a new Telnet client session on the server taken from the `self.options` dict.
            This session always fails.

        :param my_ip: IP of this Client itself
        """
        password = self.options['password']
        server_host = self.options['server']
        server_port = self.options['port']
        honeypot_id = self.options['honeypot_id']

        session = self.create_session(server_host, server_port, honeypot_id)
        self.sessions[session.id] = session

        logger.debug(
            'Sending {0} bait session to {1}:{2}. (bait id: {3})'.format('vnc', server_host, server_port, session.id))
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client_socket.connect((server_host, int(server_port)))
            session.source_port = client_socket.getsockname()[1]

        except socket.error as e:
            logger.debug('Caught exception: {0} ({1})'.format(e, str(type(e))))
        else:
            session.did_connect = True
            protocol_version = client_socket.recv(1024)
            client_socket.send(RFB_VERSION)
            supported_auth_methods = client_socket.recv(1024)

            # \x02 implies that VNC authentication method is to be used
            # Refer to http://tools.ietf.org/html/rfc6143#section-7.1.2 for more info.
            if '\x02' in supported_auth_methods:
                client_socket.send(VNC_AUTH)
            challenge = client_socket.recv(1024)

            # password limit for vnc in 8 chars
            aligned_password = (password + '\0' * 8)[:8]
            des = RFBDes(aligned_password)
            response = des.encrypt(challenge)

            client_socket.send(response)
            auth_status = client_socket.recv(1024)
            if auth_status == AUTH_SUCCESSFUL:
                session.add_auth_attempt('des_challenge', True, password=aligned_password)
                session.did_login = True
            else:
                session.add_auth_attempt('des_challenge', False, password=aligned_password)
                session.did_login = False
            session.did_complete = True

        finally:
            session.alldone = True
            session.end_session()
