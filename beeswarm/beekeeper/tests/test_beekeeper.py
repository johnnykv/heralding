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
import os
import shutil
from beeswarm.beekeeper.beekeeper import Beekeeper

gevent.monkey.patch_all()

import unittest


class Beekeeper_Tests(unittest.TestCase):

    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        test_config_file = os.path.join(os.path.dirname(__file__), 'beeswarmcfg.json.test')
        shutil.copy(test_config_file, os.path.join(self.work_dir, 'beeswarmcfg.json'))
        self.key = os.path.join(os.path.dirname(__file__), 'dummy_key.key')
        self.cert = os.path.join(os.path.dirname(__file__), 'dummy_cert.crt')

    def test_init(self):
        bk = Beekeeper(self.work_dir, None)

    def test_start(self):
        bk = Beekeeper(self.work_dir, None)
        gevent.spawn(bk.start, maintenance=False)
        gevent.sleep(1)
        self.assertNotEquals(bk.servers, {})
