# Copyright (C) 2014 Johnny Vestergaard <jkv@unixcluster.dk>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import unittest
import uuid
from datetime import datetime
import json

import zmq.green as zmq
import gevent

import beeswarm.shared
from beeswarm.server.db import database_setup
from beeswarm.server.db.entities import Honeypot
from beeswarm.server.db.entities import Session
from beeswarm.drones.honeypot.models.session import Session as HoneypotSession
from beeswarm.shared.socket_enum import SocketNames
from beeswarm.shared.message_enum import Messages
from beeswarm.server.db.session_persister import SessionPersister


class ClassifierTests(unittest.TestCase):
    def setUp(self):
        beeswarm.shared.zmq_context = zmq.Context()

    def tearDown(self):
        database_setup.clear_db()

    def test_matching(self):
        """
        Tests that attack sessions coming in quick succession are classified as probes.
        This test relates to issue #218
        """

        database_setup.setup_db('sqlite://')

        honeypot_id = 1
        honeypot = Honeypot(id=honeypot_id)

        db_session = database_setup.get_session()
        db_session.add(honeypot)
        db_session.commit()

        raw_session_publisher = beeswarm.shared.zmq_context.socket(zmq.PUB)
        raw_session_publisher.bind(SocketNames.RAW_SESSIONS)

        # startup session database
        persistence_actor = SessionPersister(999, delay_seconds=2)
        persistence_actor.start()
        gevent.sleep(1)

        for x in xrange(0, 100):
            honeypot_session = HoneypotSession(source_ip='192.168.100.22', source_port=52311, protocol='pop3', users={},
                                               destination_port=110)
            honeypot_session.try_auth('plaintext', username='james', password='bond')
            honeypot_session.honeypot_id = honeypot_id
            raw_session_publisher.send('{0} {1} {2}'.format(Messages.SESSION_HONEYPOT, honeypot_id,
                                                            json.dumps(honeypot_session.to_dict(), default=json_default,
                                                            ensure_ascii=False)))
        gevent.sleep(5)

        sessions = db_session.query(Session).all()

        for session in sessions:
            self.assertEqual(session.classification_id, 'bruteforce')

        self.assertEqual(len(sessions), 100)


def json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, uuid.UUID):
        return str(obj)
    else:
        return None
