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

import unittest
from datetime import datetime, timedelta
from pony.orm import commit

import gevent.monkey
gevent.monkey.patch_all()

#find better way to do this!
from beeswarm.beekeeper.db import database_config
database_config.setup_db(':memory:')

from beeswarm.beekeeper.db.database import Hive, Classification, Feeder, Session, Honeybee
from beeswarm.beekeeper.classifier.classifier import Classifier


class ClassifierTests(unittest.TestCase):
    def tearDown(self):
        #ensure clean db for every test run
        database_config.clear_db()

    def test_matching_session(self):
        """
        Tests if the classifier can match a honeybee with a session.
        """

        feeder = Feeder(id='f1')
        hive = Hive(id='h1')
        h = Honeybee(id='id222', username='a', password='a', source_ip='321', destination_ip='123',
                     received=datetime.now(), timestamp=datetime.now(), protocol='pop3', source_port=1,
                     destination_port=1, feeder=feeder, hive=hive)

        #session2 is the matching session
        for id, offset in (('session1', -15), ('session2', 3), ('session3', 15)):
            Session(id=id, username='a', password='a', source_ip='321', destination_ip='123',
                    received=datetime.now(), timestamp=h.timestamp + timedelta(seconds=offset),
                    protocol='pop3', source_port=1, destination_port=1, hive=hive)
        commit()

        c = Classifier()
        result = c.get_matching_session(h)
        self.assertEqual('session2', result.id)

