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
            #get all bees with no classification
            honeybees = select(h for h in Honeybee if h.classification == None)
            for h in honeybees:
                session_match = self.get_matching_session(honeybees)
                #a match means that the traffic is legit (eg. honeybee traffic)
                if session_match:
                    #confirm (classify) the honeybee and delete the hive session.
                    h.classification = Classification.get(type='honeybee')
                    session_match.delete()
            commit()

            gevent.sleep(10)

    #match honeybee with session
    def get_matching_session(self, honeybee):
        min_datetime = honeybee.timestamp - datetime.timedelta(seconds=5)
        max_datetime = honeybee.timestamp + datetime.timedelta(seconds=5)
        session_match = Session.get(lambda s: s.protocol == honeybee.protocol and
                                              s.username == honeybee.username and
                                              s.password == honeybee.password and
                                              s.hive == honeybee.hive and
                                              s.timestamp >= min_datetime and
                                              s.timestamp <= max_datetime and
                                              s.classtype != 'Honeybee')
        return session_match

    def stop(self):
        self.enabled = False