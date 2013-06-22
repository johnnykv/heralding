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

import logging
import datetime
import gevent
from beeswarm.beekeeper.db import database
from beeswarm.beekeeper.db.entities import Classification, Honeybee, Session


logger = logging.getLogger(__name__)


class Classifier(object):
    def __init__(self):
        self.enabled = False

    def start(self):
        self.enabled = True
        while self.enabled:
            db_session = database.get_session()
            self.classify_honeybees(db_session=db_session)
            self.classify_sessions(db_session=db_session)
            db_session.commit()
            gevent.sleep(10)

    #match honeybee with session
    def get_matching_session(self, honeybee, timediff=5, db_session=None):
        """
        Provided a honeybee object a matching session is returned. If no matching
        session is found None is returned.

        :param honeybee: honeybee object which will be used as base for query.
        :param timediff: +/- allowed time difference between a honeybee and a potential matching session.
        """
        min_datetime = honeybee.timestamp - datetime.timedelta(seconds=timediff)
        max_datetime = honeybee.timestamp + datetime.timedelta(seconds=timediff)

        if not db_session:
            db_session = database.get_session()

        session_match = db_session.query(Session).filter(Session.protocol == honeybee.protocol) \
            .filter(Session.hive == honeybee.hive) \
            .filter(Session.timestamp >= min_datetime) \
            .filter(Session.timestamp <= max_datetime) \
            .filter(Session.discriminator == None).first()

        return session_match

    def classify_honeybees(self, delay_seconds=30, db_session=None):
        """
        Will classify all unclassified honeybees as either legit or malicious activity. A honeybee can e.g. be classified
        as involved in malicious activity if the honeybee is subject to a MiTM attack.

        :param delay_seconds: no honeybees newer than (now - delay_seconds) will be processed.
        """
        min_datetime = datetime.datetime.utcnow() - datetime.timedelta(seconds=delay_seconds)

        if not db_session:
            db_session = database.get_session()

        honeybees = db_session.query(Honeybee).filter(Honeybee.classification == None) \
            .filter(Honeybee.did_complete == True) \
            .filter(Honeybee.timestamp < min_datetime).all()

        for h in honeybees:
            session_match = self.get_matching_session(h, db_session=db_session)
            #if we have a match this is legit honeybee traffic
            if session_match:
                logger.debug('Classifying honeybee with id {0} as legit honeybee traffic and deleting '
                             'matching session with id {1}'.format(h.id, session_match.id))
                h.classification = db_session.query(Classification).filter(Classification.type == 'honeybee').one()
                db_session.delete(session_match)
            #else we classify it as a MiTM attack
            else:
                h.classification = db_session.query(Classification).filter(Classification.type == 'mitm_1').one()

        db_session.commit()


    def classify_sessions(self, delay_seconds=30, db_session=None):
        """
        Will classify all sessions (which are not honeybees) as malicious activity. Note: The classify_honeybees method
        should be called before this method.

        :param delay_seconds: no sessions newer than (now - delay_seconds) will be processed.
        """
        min_datetime = datetime.datetime.utcnow() - datetime.timedelta(seconds=delay_seconds)

        if not db_session:
            db_session = database.get_session()

        sessions = db_session.query(Session).filter(Session.discriminator == None) \
                                            .filter(Session.timestamp <= min_datetime) \
                                            .all()

        for s in sessions:
            if s.password == None or s.username == None:
                # '== None' is a temporary solution until we have figured out the final model for Session
                logger.debug('Classifying session with id {0} as bruteforce attempt.'.format(s.id))
                s.classification = db_session.query(Classification).filter(Classification.type == 'malicious_brute').one()
            else:
                honey_matches = db_session.query(Honeybee).filter(Honeybee.username == s.username) \
                                                          .filter(Honeybee.password == s.password).all()
                if len(honey_matches) > 0:
                    #username/password has previously been transmitted in a honeybee
                    logger.debug('Classifying session with id {0} as attack which involved the reused '
                                 'of previously transmitted credentials.'.format(s.id))
                    s.classification = db_session.query(Classification).filter(Classification.type == 'mitm_2').one()
                else:
                    #we have never transmitted this username/password combo
                    logger.debug('Classifying session with id {0} as bruteforce attempt.'.format(s.id))
                    s.classification = db_session.query(Classification).filter(
                        Classification.type == 'malicious_brute').one()
        db_session.commit()

    def stop(self):
        self.enabled = False