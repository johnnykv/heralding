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

import gevent
import gevent.monkey
import tempfile
import shutil
import os
import time

gevent.monkey.patch_all()

import unittest
from beeswarm.feeder.feeder import Feeder


class Feeder_Tests(unittest.TestCase):

    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        self.test_config_file = os.path.join(os.path.dirname(__file__), 'feedercfg.json.test')

    def test_init(self):
        """Tests if the Hive class can be instantiated successfully using the default configuration file"""
        sut = Feeder(self.work_dir, config_arg=self.test_config_file)
