# Copyright (C) 2013 Aniket Panse <contact@aniketpanse.in>
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
import random
import datetime

import gevent
from gevent import Greenlet


logger = logging.getLogger(__name__)


class BaitDispatcher(Greenlet):
    """ Dispatches capabilities in a realistic fashion (with respect to timings) """

    def __init__(self, sessions, bait_type, bait_options):
        Greenlet.__init__(self)
        self.options = bait_options
        self.enabled = False
        self.bait_type = bait_type
        self.run_flag = True
        # my_ip and sessions should be moved from here
        self.sessions = sessions
        try:
            self.set_active_interval()
        except (ValueError, AttributeError, KeyError, IndexError) as err:
            logger.debug('Caught exception: {0} ({1})'.format(err, str(type(err))))

        self.activation_probability = self.options['activation_probability']
        self.sleep_interval = float(self.options['sleep_interval'])

    def set_active_interval(self):
        interval_string = self.options['active_range']
        begin, end = interval_string.split('-')
        begin = begin.strip()
        end = end.strip()
        begin_hours, begin_min = begin.split(':')
        end_hours, end_min = end.split(':')
        self.start_time = datetime.time(int(begin_hours), int(begin_min))
        self.end_time = datetime.time(int(end_hours), int(end_min))

    def _run(self):
        while self.run_flag:
            while not self.time_in_range():
                gevent.sleep(5)
            while self.time_in_range():
                if self.activation_probability >= random.random():
                    # TODO: sessions whould be moved from here, too many has knowledge of the sessions list
                    bait = self.bait_type(self.sessions, self.options)
                    gevent.spawn(bait.start)
                gevent.sleep(self.sleep_interval)

    def time_in_range(self):
        """Return true if current time is in the active range"""
        curr = datetime.datetime.now().time()
        if self.start_time <= self.end_time:
            return self.start_time <= curr <= self.end_time
        else:
            return self.start_time <= curr or curr <= self.end_time
