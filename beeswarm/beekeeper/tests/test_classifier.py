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

from beeswarm.beekeeper.db import database
from beeswarm.beekeeper.db.entities import Feeder, Hive
from beeswarm.beekeeper.db.entities import Classification, Session, Honeybee, Authentication
from beeswarm.beekeeper.classifier.classifier import Classifier


class ClassifierTests(unittest.TestCase):
    def setUp(self):
        #'sqlite://' gives a in-memory sqlite database
        database.setup_db('sqlite://')

        self.feeder_id = str(uuid.uuid4())
        self.hive_id = str(uuid.uuid4())
        self.honeybee_id = str(uuid.uuid4())
        self.honeybee_datetime = datetime.utcnow()

        db_session = database.get_session()
        feeder = Feeder(id=self.feeder_id)
        hive = Hive(id=self.hive_id)

        honeybee = Honeybee(id=self.honeybee_id, source_ip='321', destination_ip='123',
                            received=datetime.utcnow(), timestamp=self.honeybee_datetime, protocol='pop3',
                            source_port=1, destination_port=1, did_complete=True, feeder=feeder, hive=hive)

        authentication = Authentication(id=str(uuid.uuid4()), username='a', password='a',
                                        successful=True, timestamp=datetime.utcnow())
        honeybee.authentication.append(authentication)
        db_session.add_all([feeder, hive, honeybee])
        db_session.commit()

    def tearDown(self):
        database.clear_db()

    def test_matching_session(self):
        """
        Test if the get_matching_session method returns the session that matches the given honeybee.
        """

        db_session = database.get_session()
        honeybee = db_session.query(Honeybee).filter(Honeybee.id == self.honeybee_id).one()
        hive = db_session.query(Hive).filter(Hive.id == self.hive_id).one()

        #session2 is the matching session
        for id, offset in (('session1', -15), ('session2', 3), ('session3', 15)):
            s = Session(id=id, source_ip='321', destination_ip='123',
                        received=datetime.utcnow(), timestamp=honeybee.timestamp + timedelta(seconds=offset),
                        protocol='pop3', source_port=1, destination_port=1, hive=hive)
            a = Authentication(id=str(uuid.uuid4()), username='a', password='a', successful=True,
                               timestamp=datetime.utcnow())
            s.authentication.append(a)
            db_session.add(s)
        db_session.commit()

        classifier = Classifier()
        result = classifier.get_matching_session(honeybee)

        self.assertEqual('session2', result.id)

    def test_correlation_honeybee_session(self):
        """
        Test if honeybee session is correctly identified as related to a specific hive session.
        We expect the honeybee entity to be classified as a legit (successfully completed) 'honeybee' and that the hive
        session is deleted.
        """

        #setup the hive session we expect to match the honeybee
        db_session = database.get_session()
        hive = db_session.query(Hive).filter(Hive.id == self.hive_id).one()

        s_id = str(uuid.uuid4())
        s = Session(id=s_id, source_ip='321', destination_ip='123',
                    received=datetime.now(), timestamp=self.honeybee_datetime - timedelta(seconds=2),
                    protocol='pop3', source_port=1, destination_port=1, hive=hive)
        a = Authentication(id=str(uuid.uuid4()), username='a', password='a', successful=True,
                           timestamp=datetime.utcnow())
        s.authentication.append(a)
        db_session.add(s)
        db_session.commit()

        c = Classifier()
        c.classify_honeybees(0)

        honeybee = db_session.query(Honeybee).filter(Honeybee.id == self.honeybee_id).one()
        session = db_session.query(Session).filter(Session.id == s_id).first()

        #test that the honeybee got classified
        self.assertTrue(
            honeybee.classification == db_session.query(Classification).filter(Classification.type == 'honeybee').one())
        #test that the hive session got deleted
        self.assertIsNone(session)

    def test_classify_sessions_bruteforce(self):
        """
        Test if 'standalone' sessions older than X seconds get classified as brute-force attempts.
        """

        db_session = database.get_session()
        hive = db_session.query(Hive).filter(Hive.id == self.hive_id).one()

        for id, offset in (('session99', -30), ('session88', -10), ('session77', -2)):
            s = Session(id=id, source_ip='321', destination_ip='123',
                        received=datetime.utcnow(), timestamp=datetime.utcnow() + timedelta(seconds=offset),
                        protocol='pop3', source_port=1, destination_port=1, hive=hive)
            a = Authentication(id=str(uuid.uuid4()), username='he', password='haha')
            s.authentication.append(a)
            db_session.add(s)
        db_session.commit()

        c = Classifier()
        c.classify_sessions(5)

        result = db_session.query(Session).filter(Session.classification_id == 'malicious_brute').all()
        #we expect the resultset to contain session1 and session2
        self.assertEquals(len(result), 2)

    def test_classify_sessions_reuse_credentails(self):
        """
        Test if attack which uses previously transmitted credentials is tagged correctly
        """

        db_session = database.get_session()
        hive = db_session.query(Hive).filter(Hive.id == self.hive_id).one()

        s = Session(id='session1010', source_ip='321', destination_ip='123',
                    received=datetime.utcnow(), timestamp=datetime.utcnow() + timedelta(seconds=-25),
                    protocol='pop3', source_port=1, destination_port=1, hive=hive)
        a = Authentication(id=str(uuid.uuid4()), username='a', password='a')
        s.authentication.append(a)
        db_session.add(s)
        db_session.commit()

        c = Classifier()
        c.classify_sessions(0, db_session)

        result = db_session.query(Session).filter(Session.classification_id == 'mitm_2').one()
        #we expect the resultset to contain session1010
        self.assertEquals(result.id, 'session1010')
