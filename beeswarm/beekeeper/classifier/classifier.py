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
from pony.orm import commit, select
from beeswarm.beekeeper.db.database import Feeder, Hive, Classification, Honeybee, Session

logger = logging.getLogger(__name__)


class Classifier(object):
    def __init__(self):
        self.enabled = False

    def start(self):
        self.enabled = True
        while self.enabled:
            self.classify_honeybees()
            self.classify_sessions()
            commit()
            gevent.sleep(10)

    #match honeybee with session
    def get_matching_session(self, honeybee, timediff=5):
        """
        Provided a honeybee object a matching session is returned. If no matching
        session is found None is returned.

        :param honeybee: honeybee object which will be used as base for query.
        :param timediff: +/- allowed time difference between a honeybee and a potential matching session.
        """
        min_datetime = honeybee.timestamp - datetime.timedelta(seconds=timediff)
        max_datetime = honeybee.timestamp + datetime.timedelta(seconds=timediff)
        session_match = Session.get(lambda s: s.protocol == honeybee.protocol and
                                              s.hive == honeybee.hive and
                                              s.timestamp >= min_datetime and
                                              s.timestamp <= max_datetime and
                                              s.classtype != 'Honeybee')
        return session_match

    def classify_honeybees(self, delay_seconds=30):
        """
        Will classify all unclassified honeybees as either legit or malicious activity. A honeybee can e.g. be classified
        as involved in malicious activity if the honeybee is subject to a MiTM attack.

        :param delay_seconds: no honeybees newer than (now - delay_seconds) will be processed.
        """
        min_datetime = datetime.datetime.utcnow() - datetime.timedelta(seconds=delay_seconds)

        honeybees = select(h for h in Honeybee if h.classification == None and
                                                  h.did_complete and
                                                  h.timestamp < min_datetime)
        for h in honeybees:
            session_match = self.get_matching_session(h)
            #if we have a match this is legit honeybee traffic
            if session_match:
                logger.debug('Classifying honeybee with id {0} as legit honeybee traffic and deleting '
                             'matching session with id {1}'.format(h.id, session_match.id))
                h.classification = Classification.get(type='honeybee')
                session_match.delete()
            #else we classify it as a MiTM attack
            else:
                h.classification = Classification.get(type='mitm_1')

    def classify_sessions(self, delay_seconds=30):
        """
        Will classify all sessions (which are not honeybees) as malicious activity. Note: The classify_honeybees method
        should be called before this method.

        :param delay_seconds: no sessions newer than (now - delay_seconds) will be processed.
        """
        min_datetime = datetime.datetime.utcnow() - datetime.timedelta(seconds=delay_seconds)

        sessions = select(s for s in Session if s.classification == None and
                                                s.classtype == 'Session' and
                                                s.timestamp <= min_datetime)
        #sessions are classified as brute-force attempts (until further notice...)
        for s in sessions:
            if s.password == None or s.username == None:
                logger.debug('Classifying session with id {0} as bruteforce attempt.'.format(s.id))
                s.classification = Classification.get(type='malicious_brute')
            else:
                honey_matches = select(h for h in Honeybee if h.username == s.username and
                                                              h.password == s.username)
                if len(honey_matches) > 0:
                    logger.debug('Classifying session with id {0} as bruteforce attempt.'.format(s.id))
                    s.classification = Classification.get(type='mitm_2')
                else:
                    logger.debug('Classifying session with id {0} as bruteforce attempt.'.format(s.id))
                    s.classification = Classification.get(type='malicious_brute')

    def stop(self):
        self.enabled = False