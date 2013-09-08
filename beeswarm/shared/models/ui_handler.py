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

import curses
import time


class UIHandler(object):

    def __init__(self, status):
        self.status = status
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.screen.keypad(1)
        self.height, self.width = self.screen.getmaxyx()
        self.run_flag = False
        self.run()

    def run(self):
        self.run_flag = True
        while True:
            self.screen.clear()
            self.screen.addstr(0, (self.width-len(self.status['mode']))/2, self.status['mode'])
            self.screen.refresh()
            time.sleep(1)

    def stop(self):
        self.run_flag = False
        curses.initscr()
        curses.nocbreak()
        curses.echo()
        curses.endwin()

