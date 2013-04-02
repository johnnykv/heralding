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
from argparse import ArgumentParser
import sys

import gevent
import gevent.monkey
from gevent import Greenlet

from hive.hive import Hive, ConfigNotFound


gevent.monkey.patch_all()

logger = logging.getLogger()


def setuplogging(logfile, verbose):

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)-15s (%(name)s) %(message)s')
    console_log = logging.StreamHandler()

    if verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO

    console_log.addFilter(LogFilter())
    console_log.setLevel(loglevel)
    console_log.setFormatter(formatter)
    root_logger.addHandler(console_log)

    file_log = logging.FileHandler(logfile)
    file_log.setLevel(logging.DEBUG)
    file_log.setFormatter(formatter)
    root_logger.addHandler(file_log)


class LogFilter(logging.Filter):
    def filter(self, rec):
        if rec.name == 'paramiko.transport':
            return False
        else:
            return True

if __name__ == '__main__':
    parser = ArgumentParser(description='Beeswarm Hive')
    parser.add_argument('--config', dest='config_file', default='hive.cfg')
    parser.add_argument('--logfile', dest='logfile', default='hive.log')
    parser.add_argument('-v', action='store_true', default=False,
                        help='Output more verbose information to console. This will include usernames and passwords.')
    args = parser.parse_args()

    try:
        setuplogging(args.logfile, args.v)
        the_hive = Hive('hive.cfg')
    except ConfigNotFound as ex:
        logger.error(ex)
        sys.exit(ex)

    hive_greenlet = Greenlet.spawn(the_hive.start_serving)

    try:
        gevent.joinall([hive_greenlet])
    except KeyboardInterrupt as ex:
        the_hive.stop_serving()

    gevent.joinall([hive_greenlet], 5)
