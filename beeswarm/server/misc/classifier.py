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
from beeswarm.server.db.entities import Classification, BaitSession, Session, Authentication


logger = logging.getLogger(__name__)


class Classifier(object):
    def __init(self):
        self.enabled = True

    def classify_sessions(self, delay_seconds=30, db_session=None):
        """
        Will classify all unclassified bait_sessions as either legit or malicious activity. A bait session can e.g. be classified
        as involved in malicious activity if the bait session is subject to a MiTM attack.

        :param delay_seconds: no bait_sessions newer than (now - delay_seconds) will be processed.
        """
        min_datetime = datetime.datetime.utcnow() - datetime.timedelta(seconds=delay_seconds)

        if not db_session:
            db_session = database_setup.get_session()

        bait_sessions = db_session.query(BaitSession).options(joinedload(BaitSession.authentication)) \
            .filter(BaitSession.classification_id == 'pending') \
            .filter(BaitSession.did_complete == True) \
            .filter(BaitSession.received < min_datetime).all()

        for bait_session in bait_sessions:
            logger.debug('Classifying bait session with id {0} as MITM'.format(bait_session.id))
            bait_session.classification = db_session.query(Classification).filter(Classification.type == 'mitm').one()

        sessions = db_session.query(Session).filter(Session.discriminator == None) \
            .filter(Session.timestamp <= min_datetime) \
            .filter(Session.classification_id == 'pending') \
            .all()

        for session in sessions:
            # Check if the attack used credentials leaked by beeswarm drones
            for a in session.authentication:
                bait_match = db_session.query(BaitSession)\
                    .filter(BaitSession.authentication.any(username=a.username, password=a.password)).first()
                if bait_match:
                    break

            if bait_match:
                logger.debug('Classifying session with id {0} as attack which involved the reused '
                             'of previously transmitted credentials.'.format(session.id))
                session.classification = db_session.query(Classification).filter(
                    Classification.type == 'credentials_reuse').one()
            elif len(session.authentication) == 0:
                logger.debug('Classifying session with id {0} as probe.'.format(session.id))
                session.classification = db_session.query(Classification).filter(Classification.type == 'probe').one()
            else:
                # we have never transmitted this username/password combo
                logger.debug('Classifying session with id {0} as bruteforce attempt.'.format(session.id))
                session.classification = db_session.query(Classification).filter(
                    Classification.type == 'bruteforce').one()

        db_session.commit()

    def stop(self):
        self.enabled = False