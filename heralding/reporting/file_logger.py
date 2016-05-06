# Copyright (C) 2016 Johnny Vestergaard <jkv@unixcluster.dk>
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
import csv
import os
from base_logger import BaseLogger

logger = logging.getLogger(__name__)


class FileLogger(BaseLogger):
    def __init__(self, logFile):
        super(FileLogger, self).__init__()

        if not os.path.isfile(logFile):
            self.fileHandler = open(logFile, 'w')
        else:
            self.fileHandler = open(logFile, 'a')

        fieldNames = ['timestamp', 'auth_id', 'session_id', 'source_ip', 'source_port', 'destination_ip',
                      'destination_port', 'protocol', 'username', 'password']
        self.csvWriter = csv.DictWriter(self.fileHandler, fieldnames=fieldNames, extrasaction='ignore')

        # empty file, write csv header
        if os.path.getsize(logFile) == 0:
            self.csvWriter.writeheader()
            self.fileHandler.flush()

        logger.info('File logger started, using file: {0}'.format(logFile))

    def loggerStopped(self):
        self.fileHandler.Flush()
        self.fileHandler.close()


    def handle_log_data(self, data):
        self.csvWriter.writerow(data)
        # meh
        self.fileHandler.flush()
