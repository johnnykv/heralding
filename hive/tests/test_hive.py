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

gevent.monkey.patch_all()

import unittest
from hive.hive import Hive


class hive_tests(unittest.TestCase):
    def test_init(self):
        """Tests if the Hive class can be instantiated successfully using the default configuration file"""

        sut = Hive(config_file='hive.cfg.dist', key='hive/tests/dummy_key.key', cert='hive/tests/dummy_cert.crt')


    def test_start_serving(self):

        sut = Hive(config_file='hive/tests/hive.cfg.test', key='hive/tests/dummy_key.key', cert='hive/tests/dummy_cert.crt')
        gevent.spawn(sut.start_serving)
        gevent.sleep(1)
        #number of capabilities (servers). This value must be updated when adding new capabilities
        self.assertEquals(5, len(sut.servers))

if __name__ == '__main__':
    unittest.main()
