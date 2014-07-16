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

import socket
import unittest
import os
import tempfile
import shutil

import gevent.monkey


gevent.monkey.patch_all()

from gevent.server import StreamServer
from beeswarm.drones.honeypot.honeypot import Honeypot
from beeswarm.drones.honeypot.capabilities import vnc
from beeswarm.shared.vnc_constants import *


class VncTests(unittest.TestCase):
    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        Honeypot.prepare_environment(self.work_dir)

    def tearDown(self):
        if os.path.isdir(self.work_dir):
            shutil.rmtree(self.work_dir)

    def test_connection(self):
        """ Tests if the VNC capability is up, and tries login.
        """
        sessions = {}

        options = {'enabled': 'True', 'port': 0, 'users': {'test': 'test'}}
        cap = vnc.vnc(sessions, options, self.work_dir)
        srv = StreamServer(('0.0.0.0', 0), cap.handle_session)
        srv.start()

        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(('127.0.0.1', srv.server_port))

        protocol_version = client_socket.recv(1024)
        self.assertEquals(protocol_version, 'RFB 003.007\n')

        client_socket.send(RFB_VERSION)
        supported_auth_methods = client_socket.recv(1024)
        self.assertEquals(supported_auth_methods, SUPPORTED_AUTH_METHODS)

        client_socket.send(VNC_AUTH)
        challenge = client_socket.recv(1024)

        # Send 16 bytes because server expects them. Don't care what they
        # are
        client_socket.send('\x00' * 16)
        auth_status = client_socket.recv(1024)
        self.assertEquals(auth_status, AUTH_FAILED)
