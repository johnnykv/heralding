# Copyright (C) 2012 Johnny Vestergaard <jkv@unixcluster.dk>
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

import gevent
import gevent.monkey
import sys
from hive.hive import Hive, ConfigNotFound
from argparse import ArgumentParser

gevent.monkey.patch_all()

import logging

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

    console_log.setLevel(loglevel)
    console_log.setFormatter(formatter)
    root_logger.addHandler(console_log)

    file_log = logging.FileHandler(logfile)
    file_log.setLevel(logging.DEBUG)
    file_log.setFormatter(formatter)
    root_logger.addHandler(file_log)

if __name__ == '__main__':
    parser = ArgumentParser(description='Beeswarm Hive')
    parser.add_argument('--config', dest='config_file', default='hive.cfg')
    parser.add_argument('--logfile', dest='logfile', default='hive.log')
    parser.add_argument('-v', action='store_true', default=False,
                        help='Output more verbose information to console. This will include usernames and passwords.')
    args = parser.parse_args()
    print "end"

    try:
        setuplogging(args.logfile, args.v)
        main_hive = Hive('hive.cfg')
    except ConfigNotFound as ex:
        logger.error(ex)
        sys.exit(ex)

    try:
        main_hive.start_serving()
    except KeyboardInterrupt as ex:
        main_hive.stop_serving()
