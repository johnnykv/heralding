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
import uuid
from datetime import datetime, timedelta
from pony.orm import commit, select

import gevent.monkey

gevent.monkey.patch_all()

#find better way to do this!
from beeswarm.beekeeper.db import database_config

database_config.setup_db(':memory:')

from beeswarm.beekeeper.db.database import Hive, Classification, Feeder, Session, Honeybee
from beeswarm.beekeeper.classifier.classifier import Classifier


class ClassifierTests(unittest.TestCase):
    def setUp(self):
        self.feeder_id = str(uuid.uuid4())
        self.hive_id = str(uuid.uuid4())
        self.honeybee_id = str(uuid.uuid4())

        self.feeder = Feeder(id=self.feeder_id)
        self.hive = Hive(id=self.hive_id)
        self.honeybee = Honeybee(id=self.honeybee_id, username='a', password='a', source_ip='321', destination_ip='123',
                                 received=datetime.now(), timestamp=datetime.now(), protocol='pop3', source_port=1,
                                 destination_port=1, feeder=self.feeder, hive=self.hive)

        self.tmp_sessions = []

        commit()

    def tearDown(self):
        #delete test-case specific data
        for e in self.tmp_sessions:
            e.delete()

    def test_matching_session(self):
        """
        Test if the get_matching_session method returns the session which matches a given honeybee.
        """

        #session2 is the matching session
        t = []
        for id, offset in (('session1', -15), ('session2', 3), ('session3', 15)):
            s = Session(id=id, username='a', password='a', source_ip='321', destination_ip='123',
                        received=datetime.now(), timestamp=self.honeybee.timestamp + timedelta(seconds=offset),
                        protocol='pop3', source_port=1, destination_port=1, hive=self.hive)
            self.tmp_sessions.append(s)
        commit()

        c = Classifier()
        result = c.get_matching_session(self.honeybee)
        self.assertEqual('session2', result.id)

    def test_classify_sessions(self):
        """
        Test if 'standalone' sessions older than X seconds get classified as brute-force attempts.
        """
        database_config.clear_db()
        for id, offset in (('session1', -30), ('session2', -10), ('session3', -2)):
            s = Session(id=id, username='a', password='a', source_ip='321', destination_ip='123',
                        received=datetime.now(), timestamp=datetime.now() + timedelta(seconds=offset),
                        protocol='pop3', source_port=1, destination_port=1, hive=self.hive)
            self.tmp_sessions.append(s)
        commit()

        c = Classifier()
        c.classify_sessions(5)
        commit()

        result = select(a for a in Session if a.classtype == 'Session' and
                                              a.classification == Classification.get(type='malicious_brute'))

        #we expect the resultset to contain session1 and session2
        self.assertEquals(len(result), 2)


