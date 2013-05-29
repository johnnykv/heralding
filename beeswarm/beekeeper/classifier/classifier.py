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

    def classify_honeybees(self):
        honeybees = select(h for h in Honeybee if h.classification == None)
        for h in honeybees:
            session_match = self.get_matching_session(honeybees)
            #a match means that the traffic is legit (eg. honeybee traffic)
            if session_match:
                logger.debug('Classifying honeybee with id {0} as successfull honeybee traffic and deleting '
                             'matching sessions with id {1}'.format(h.id, session_match.id))
                h.classification = Classification.get(type='honeybee')
                session_match.delete()

    def classify_sessions(self, delay_seconds):
        min_datetime = datetime.datetime.now() - datetime.timedelta(seconds=delay_seconds)
        print min_datetime
        sessions = select(s for s in Session if s.classification == None and
                                                s.classtype == 'Session' and
                                                s.timestamp <= min_datetime)
        #sessions are classified as brute-force attempts (until further notice...)
        for s in sessions:
            logger.debug('Classifying session with id {0} as bruteforce attempt.'.format(s.id))
            s.classification = Classification.get(type='malicious_brute')

    def stop(self):
        self.enabled = False