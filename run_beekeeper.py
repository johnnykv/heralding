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

from beekeeper.beekeeper import Beekeeper

logger = logging.getLogger()


def setuplogging(logfile):

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)-15s (%(name)s) %(message)s')

    console_log = logging.StreamHandler()
    console_log.setLevel(logging.DEBUG)
    console_log.setFormatter(formatter)
    root_logger.addHandler(console_log)

    file_log = logging.FileHandler(logfile)
    file_log.setLevel(logging.DEBUG)
    file_log.setFormatter(formatter)
    root_logger.addHandler(file_log)


if __name__ == '__main__':
    parser = ArgumentParser(description='Beeswarm Beekeeper')
    parser.add_argument('--config', dest='config_file', default='beekeeper.cfg')
    parser.add_argument('--logfile', dest='logfile', default='beekeeper.log')
    args = parser.parse_args()

    setuplogging(args.logfile)
    the_keeper = Beekeeper()
    #this blocks
    the_keeper.start_serving()