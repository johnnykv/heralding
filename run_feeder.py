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

import gevent
import gevent.monkey
gevent.monkey.patch_all()
from gevent import Greenlet

import logging
from argparse import ArgumentParser
import sys

from feeder.feeder import Feeder, ConfigNotFound
from ConfigParser import NoSectionError, NoOptionError

logger = logging.getLogger()


def setuplogging(logfile):

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)-15s (%(name)s) %(message)s')
    console_log = logging.StreamHandler()

    loglevel = logging.DEBUG

    console_log.setLevel(loglevel)
    console_log.setFormatter(formatter)
    root_logger.addHandler(console_log)

    file_log = logging.FileHandler(logfile)
    file_log.setLevel(logging.DEBUG)
    file_log.setFormatter(formatter)
    root_logger.addHandler(file_log)


if __name__ == '__main__':
    parser = ArgumentParser(description='Beeswarm Feeder')
    parser.add_argument('--config', dest='config_file', default='feeder.cfg')
    parser.add_argument('--logfile', dest='logfile', default='feeder.log')
    args = parser.parse_args()

    try:
        setuplogging(args.logfile)
        the_feeder = Feeder(args.config_file)
    except ConfigNotFound as ex:
        logger.error(ex)
        sys.exit(ex)
    except (NoSectionError, NoOptionError) as ex:
        logger.error('Error while parsing config file. Please check hive.cfg.dist to see if any '
                     'options has changed since last update. ({0})'.format(ex))
        sys.exit(ex)

    feeder_greenlet = Greenlet.spawn(the_feeder.start_feeding)

    try:
        gevent.joinall([feeder_greenlet])
    except KeyboardInterrupt as ex:
        the_feeder.stop_serving()

    gevent.joinall([feeder_greenlet], 5)
