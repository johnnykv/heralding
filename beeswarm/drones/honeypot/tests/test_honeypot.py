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
import tempfile
import shutil
import json
import os

import gevent
import gevent.monkey
import zmq.green as zmq


gevent.monkey.patch_all()

import unittest
from beeswarm.drones.honeypot.honeypot import Honeypot
from beeswarm.shared.asciify import asciify


class HoneypotTests(unittest.TestCase):
    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        Honeypot.prepare_environment(self.work_dir)

        test_config_file = os.path.join(os.path.dirname(__file__), 'honeypotcfg.json.test')
        with open(test_config_file, 'r') as config_file:
            self.config_dict = json.load(config_file, object_hook=asciify)
        self.key = os.path.join(os.path.dirname(__file__), 'dummy_key.key')
        self.cert = os.path.join(os.path.dirname(__file__), 'dummy_cert.crt')
        self.inbox = gevent.queue.Queue()
        self.mock_relay = gevent.spawn(self.mock_server_relay)

    def tearDown(self):
        if os.path.isdir(self.work_dir):
            shutil.rmtree(self.work_dir)
        self.mock_relay.kill()
        self.inbox = gevent.queue.Queue()

    def mock_server_relay(self):
        context = zmq.Context()
        internal_server_relay = context.socket(zmq.PULL)
        internal_server_relay.bind('ipc://serverRelay')

        while True:
            self.inbox.put(internal_server_relay.recv())

    def test_init(self):
        """Tests if the Honeypot class can be instantiated successfully"""
        sut = Honeypot(self.work_dir, self.config_dict, key=self.key, cert=self.cert)
        # expect two messages containing priv/pub key.
        gevent.sleep(1)
        self.assertEqual(self.inbox.qsize(), 2)

    def test_start_serving(self):
        sut = Honeypot(self.work_dir, self.config_dict, key=self.key, cert=self.cert)
        gevent.spawn(sut.start)
        gevent.sleep(1)
        # number of capabilities (workers). This value must be updated when adding new capabilities
        self.assertEquals(9, len(sut.servers))
