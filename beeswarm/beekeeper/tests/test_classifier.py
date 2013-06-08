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
        self.honeybee_datetime = datetime.utcnow()

        self.feeder = Feeder(id=self.feeder_id)
        self.hive = Hive(id=self.hive_id)
        self.honeybee = Honeybee(id=self.honeybee_id, username='a', password='a', source_ip='321', destination_ip='123',
                                 received=datetime.utcnow(), timestamp=self.honeybee_datetime, protocol='pop3',
                                 source_port=1,
                                 destination_port=1, did_complete=True, feeder=self.feeder, hive=self.hive)

        #all session stored here will get deleted on each testrun
        self.tmp_sessions = []

        commit()

    def tearDown(self):
        #delete test-case specific data
        for e in self.tmp_sessions:
            e.delete()
        self.hive.delete()
        self.honeybee.delete()
        commit()

    def test_matching_session(self):
        """
        Test if the get_matching_session method returns the session which matches a given honeybee.
        """

        #session2 is the matching session
        for id, offset in (('session1', -15), ('session2', 3), ('session3', 15)):
            s = Session(id=id, username='a', password='a', source_ip='321', destination_ip='123',
                        received=datetime.utcnow(), timestamp=self.honeybee.timestamp + timedelta(seconds=offset),
                        protocol='pop3', source_port=1, destination_port=1, hive=self.hive)
            self.tmp_sessions.append(s)
        commit()

        c = Classifier()
        result = c.get_matching_session(self.honeybee)
        self.assertEqual('session2', result.id)

    def test_correlation_honeybee_session(self):
        """
        Test if honeybee session is correctly identified as related to a specific hive session.
        We expect the honeybee entity to be classified as a legit (successfully completed) 'honeybee' and that the hive
        session is deleted.
        """
        database_config.clear_db()

        #setup the hive session we expect to match the honeybee
        s_id = str(uuid.uuid4())

        s = Session(id=s_id, username='a', password='b', source_ip='321', destination_ip='123',
                    received=datetime.now(), timestamp=self.honeybee_datetime - timedelta(seconds=2),
                    protocol='pop3', source_port=1, destination_port=1, hive=self.hive)
        self.tmp_sessions.append(s)
        commit()

        c = Classifier()
        c.classify_honeybees(0)

        honeybee = Honeybee.get(id=self.honeybee_id)
        session = Honeybee.get(id=s_id)

        #test that the honeybee got classified
        self.assertTrue(honeybee.classification == Classification.get(type='honeybee'))
        #test that the hive session got deleted
        self.assertIsNone(session)




    def test_classify_sessions_bruteforce(self):
        """
        Test if 'standalone' sessions older than X seconds get classified as brute-force attempts.
        """
        database_config.clear_db()
        for id, offset in (('session1', -30), ('session2', -10), ('session3', -2)):
            s = Session(id=id, username='b', password='b', source_ip='321', destination_ip='123',
                        received=datetime.utcnow(), timestamp=datetime.utcnow() + timedelta(seconds=offset),
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



