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
import shutil
from gevent.greenlet import Greenlet
from mock import Mock
import time
from beeswarm.feeder.models.dispatcher import BeeDispatcher

import gevent
import gevent.monkey
import tempfile
import os

gevent.monkey.patch_all()

import unittest
from beeswarm.feeder.feeder import Feeder


class Feeder_Tests(unittest.TestCase):
    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        self.test_config_file = os.path.join(os.path.dirname(__file__), 'feedercfg.json.test')

    def tearDown(self):
        if os.path.isdir(self.work_dir):
            shutil.rmtree(self.work_dir)

    def test_init(self):
        """Tests if the Hive class can be instantiated successfully using the default configuration file"""
        sut = Feeder(self.work_dir, config_arg=self.test_config_file)

    def test_dispatcher(self):
        options = {
            # NoneType because we're going to pass a None to the dispatcher.
            'bee_NoneType': {
                'enabled': True,
                'server': '127.0.0.1',
                'timing': {
                    'active_range': '00:00 - 23:59',
                    'sleep_interval': '1',
                    'activation_probability': '1'
                },
                'username': 'test',
                'password': 'test',
                'port': 8080
            },
        }

        dispatcher = BeeDispatcher(options, None, '127.0.0.1')

        dispatcher.max_sessions = 1
        dispatcher.bee = Mock()
        dispatcher_greenlet = Greenlet(dispatcher.start)
        dispatcher_greenlet.start()
        time.sleep(1)
        dispatcher_greenlet.kill()
        dispatcher.bee.do_session.assert_called()