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
import random
import gevent
from gevent.greenlet import Greenlet


class BeeDispatcher(object):

    """ Dispatches bees in a realistic fashion (with respect to timings) """

    def __init__(self, options, bee, my_ip):
        self.options = options
        self.enabled = False
        self.bee = bee
        self.coarse_flag = True
        self.fine_flag = True
        self.my_ip = my_ip
        self.max_sessions = random.randint(4, 8)
        sched_pattern = self.options['bee_' + self.bee.__class__.__name__]['timing']
        self.coarse_interval = sched_pattern['coarse']
        self.fine_interval = sched_pattern['fine']

    def start(self):
        while self.coarse_flag:
            self.dispatch_bee()
            gevent.sleep(self.coarse_interval)

    def dispatch_bee(self):
        n = 0
        while n < self.max_sessions and self.fine_flag:
            self.greenlet = Greenlet(self.bee.do_session, self.my_ip)
            self.greenlet.start()
            gevent.sleep(self.fine_interval)
            n += 1
