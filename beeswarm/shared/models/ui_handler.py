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
import logging
import time


HONEYPOT_TITLE = ""

CLIENT_TITLE = """..______............_............
.|  ____|..........| |...........
.| |__.___..___..__| |.___._.__..
.|  __/ _ \/ _ \/ _` |/ _ \ '__|.
.| |.|  __/  __/ (_| |  __/ |....
.|_|..\___|\___|\__,_|\___|_|....
"""


class CursesLogHandler(logging.Handler):
    def __init__(self, win, level=logging.DEBUG):
        logging.Handler.__init__(self, level)
        self.win = win
        maxy, maxx = win.getmaxyx()
        self.height = maxy

    def emit(self, record):
        y, x = self.win.getyx()
        if x != 0:
            #self.win.move(y+1,0)
            y += 1
        if y + 1 >= self.height:
            self.win.erase()
            y = 0

        self.win.addstr(y, 0, record.getMessage())
        self.win.refresh()


class _UIHandler(object):
    def __init__(self, status, screen):
        self.status = status
        self.height, self.width = screen.getmaxyx()
        self.screen = screen.subwin(self.height-10, self.width, 0, 0)
        self.run_flag = False
        self._draw_height = 0  # Used by the draw method to keep track of lines already drawn

    def run(self):
        self.run_flag = True
        while True:
            self.screen.clear()
            self._draw_height = 0
            self.height, self.width = self.screen.getmaxyx()
            self.draw()
            self.screen.refresh()
            time.sleep(1)

    def stop(self):
        self.run_flag = False

    def addstring_middle(self, string):
        self.screen.addstr(self._draw_height, (self.width - len(string)) / 2, string)
        self._draw_height += 1

    def addstring_left(self, string):
        string = '  {}'.format(string)
        self.screen.addstr(self._draw_height, 0, string)

    def addstring_right(self, string):
        string = '{}  '.format(string)
        self.screen.addstr(self._draw_height, self.width - len(string), string)
        self._draw_height += 1

    def draw(self):
        raise Exception('Do not call base class!')

    def draw_title(self, title_string):
        for line in title_string.split('\n'):
            line.strip('\n')
            self.addstring_middle(line)


class HoneypotUIHandler(_UIHandler):
    def draw(self):
        self.draw_title(HONEYPOT_TITLE)
        self.addstring_middle('Running: ' + ' '.join(self.status['enabled_capabilities']))
        self._draw_height += 1
        self.addstring_left('IP Address: {}'.format(self.status['ip_address']))
        self.addstring_right('Honeypot ID: {}'.format(self.status['honeypot_id']))
        self.addstring_left('Total Sessions: {}'.format(self.status['total_sessions']))
        self.addstring_right('Active Sessions: {}'.format(self.status['active_sessions']))


class ClientUIHandler(_UIHandler):
    def draw(self):
        self.draw_title(CLIENT_TITLE)
        self.addstring_middle('Running: ' + ' '.join(self.status['enabled_bees']))
        self._draw_height += 1
        self.addstring_left('IP Address: {}'.format(self.status['ip_address']))
        self.addstring_right('Client ID: {}'.format(self.status['client_id']))
        self.addstring_left('Total Bees Sent: {}'.format(self.status['total_bees']))
        self.addstring_right('Successful Bees: {}'.format(self.status['active_bees']))


def tail_log(fd, nlines=10):
    lines = [''] * nlines
    c = 0
    for line in fd:
        lines[c % nlines] = line
        c += 1
    return lines[c % nlines:]
