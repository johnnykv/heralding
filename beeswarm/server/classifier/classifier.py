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

from sqlalchemy.orm import joinedload
from beeswarm.server.db import database_setup
from beeswarm.server.db.entities import Classification, Honeybee, Session, Authentication


logger = logging.getLogger(__name__)


class Classifier(object):

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
            db_session = database_setup.get_session()

        #default return value
        match = None

        #get all sessions that matches basic properties.
        sessions = db_session.query(Session).options(joinedload(Session.authentication))\
                                            .filter(Session.protocol == honeybee.protocol) \
                                            .filter(Session.honeypot == honeybee.honeypot) \
                                            .filter(Session.timestamp >= min_datetime) \
                                            .filter(Session.timestamp <= max_datetime) \
                                            .filter(Session.protocol == honeybee.protocol) \
                                            .filter(Session.discriminator == None)

        #identify the correct session by comparing authentication.
        #this could properly also be done using some fancy ORM/SQL construct.
        for session in sessions:
            for honey_auth in honeybee.authentication:
                for session_auth in session.authentication:
                    if session_auth.username == honey_auth.username and \
                                    session_auth.password == honey_auth.password and \
                                    session_auth.successful == honey_auth.successful:
                        match = session
                        break

        return match

    def classify_honeybees(self, delay_seconds=30, db_session=None):
        """
        Will classify all unclassified honeybees as either legit or malicious activity. A honeybee can e.g. be classified
        as involved in malicious activity if the honeybee is subject to a MiTM attack.

        :param delay_seconds: no honeybees newer than (now - delay_seconds) will be processed.
        """
        min_datetime = datetime.datetime.utcnow() - datetime.timedelta(seconds=delay_seconds)

        if not db_session:
            db_session = database_setup.get_session()

        honeybees = db_session.query(Honeybee).options(joinedload(Honeybee.authentication))\
                                              .filter(Honeybee.classification_id == 'unclassified') \
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
            db_session = database_setup.get_session()

        sessions = db_session.query(Session).filter(Session.discriminator == None) \
                                            .filter(Session.timestamp <= min_datetime) \
                                            .filter(Session.classification_id == 'unclassified') \
                                            .all()

        for session in sessions:
            #TODO: This would be more pretty if done with pure orm
            honey_matches = []
            for a in session.authentication:
                honey_matches = db_session.query(Honeybee).join(Authentication)\
                                                          .filter(Authentication.username == a.username) \
                                                          .filter(Authentication.password == a.password).all()

            if len(honey_matches) > 0:
                #username/password has previously been transmitted in a honeybee
                logger.debug('Classifying session with id {0} as attack which involved the reused '
                             'of previously transmitted credentials.'.format(session.id))
                session.classification = db_session.query(Classification).filter(Classification.type == 'credentials_reuse').one()
            elif len(session.authentication) == 0:
                logger.debug('Classifying session with id {0} as probe.'.format(session.id))
                session.classification = db_session.query(Classification).filter(Classification.type == 'probe').one()
            else:
                #we have never transmitted this username/password combo
                logger.debug('Classifying session with id {0} as bruteforce attempt.'.format(session.id))
                session.classification = db_session.query(Classification).filter(
                    Classification.type == 'bruteforce').one()
        db_session.commit()

    def stop(self):
        self.enabled = False