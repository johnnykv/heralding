# Copyright (C) 2017 Johnny Vestergaard <jkv@unixcluster.dk>
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

import os
import csv
import logging

from heralding.reporting.base_logger import BaseLogger

logger = logging.getLogger(__name__)


class FileLogger(BaseLogger):
    def __init__(self, session_logfile, auth_logfile):
        super().__init__()

        auth_field_names = ['timestamp', 'auth_id', 'session_id', 'source_ip', 'source_port', 'destination_ip',
                            'destination_port', 'protocol', 'username', 'password']
        self.auth_log_filehandler, self.auth_log_writer = self.setup_file(
            auth_logfile, auth_field_names)

        session_field_names = ['timestamp', 'duration', 'session_id', 'source_ip', 'source_port', 'destination_ip',
                               'destination_port', 'protocol', 'auth_attempts']
        self.session_log_filehandler, self.session_log_writer = self.setup_file(
            session_logfile, session_field_names)

        logger.info('File logger started, using files: {0} and {1}'.format(
            auth_logfile, session_logfile))

    def setup_file(self, filename, field_names):
        handler = writer = None

        if not os.path.isfile(filename):
            handler = open(filename, 'w', encoding='utf-8')
        else:
            handler = open(filename, 'a', encoding='utf-8')

        writer = csv.DictWriter(
            handler, fieldnames=field_names, extrasaction='ignore')

        # empty file, write csv header
        if os.path.getsize(filename) == 0:
            writer.writeheader()
            handler.flush()

        return handler, writer

    def loggerStopped(self):
        self.auth_log_filehandler.flush()
        self.auth_log_filehandler.close()

    def handle_auth_log(self, data):
        # for now this logger only handles authentication attempts where we are able
        # to log both username and password
        if 'username' in data and 'password' in data:
            self.auth_log_writer.writerow(data)
            # meh
            self.auth_log_filehandler.flush()

    def handle_session_log(self, data):
        self.session_log_writer.writerow(data)
        # double meh
        self.session_log_filehandler.flush()
