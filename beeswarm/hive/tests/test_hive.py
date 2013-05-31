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
import os

gevent.monkey.patch_all()

import unittest
from beeswarm.hive.hive import Hive


class hive_tests(unittest.TestCase):
    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        Hive.prepare_environment(self.work_dir)

        self.test_config_file = os.path.join(os.path.dirname( __file__), 'hivecfg.json.test')
        self.key = os.path.join(os.path.dirname( __file__), 'dummy_key.key')
        self.cert = os.path.join(os.path.dirname( __file__), 'dummy_cert.crt')

    def tearDown(self):
        if os.path.isdir(self.work_dir):
            shutil.rmtree(self.work_dir)

    def test_init(self):
        """Tests if the Hive class can be instantiated successfully using the default configuration file"""
        sut = Hive(self.work_dir, config_file=self.test_config_file, key=self.key, cert=self.cert)


    def test_start_serving(self):

        sut = Hive(self.work_dir, config_file=self.test_config_file, key=self.key, cert=self.cert)
        gevent.spawn(sut.start)
        gevent.sleep(1)
        #number of capabilities (servers). This value must be updated when adding new capabilities
        self.assertEquals(9, len(sut.servers))

if __name__ == '__main__':
    unittest.main()
