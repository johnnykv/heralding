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
import gevent
import gevent.monkey
import tempfile
import shutil
import json
import os

gevent.monkey.patch_all()

import unittest
from beeswarm.drones.honeypot.honeypot import Honeypot
from beeswarm.shared.asciify import asciify


class honeypot_tests(unittest.TestCase):
    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        Honeypot.prepare_environment(self.work_dir)

        test_config_file = os.path.join(os.path.dirname(__file__), 'honeypotcfg.json.test')
        with open(test_config_file, 'r') as config_file:
            self.config_dict = json.load(config_file, object_hook=asciify)
        self.key = os.path.join(os.path.dirname(__file__), 'dummy_key.key')
        self.cert = os.path.join(os.path.dirname(__file__), 'dummy_cert.crt')

    def tearDown(self):
        if os.path.isdir(self.work_dir):
            shutil.rmtree(self.work_dir)

    def test_init(self):
        """Tests if the Honeypot class can be instantiated successfully using the default configuration file"""
        sut = Honeypot(self.work_dir, self.config_dict, key=self.key, cert=self.cert)

    def test_user_creation(self):
        """Tests proper generation of BaitUsers from the data in the config file"""
        sut = Honeypot(self.work_dir, self.config_dict, key=self.key, cert=self.cert)
        sut.create_users()
        self.assertEquals(1, len(sut.users))

    def test_start_serving(self):
        sut = Honeypot(self.work_dir, self.config_dict, key=self.key, cert=self.cert)
        gevent.spawn(sut.start)
        gevent.sleep(1)
        #number of capabilities (workers). This value must be updated when adding new capabilities
        self.assertEquals(9, len(sut.servers))
