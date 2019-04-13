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
import json

from heralding.reporting.base_logger import BaseLogger
import heralding

logger = logging.getLogger(__name__)


class FileLogger(BaseLogger):
    def __init__(self, session_csv_logfile, sessions_json_logfile, auth_logfile):
        super().__init__()

        self.auth_log_filehandler = None
        self.auth_log_writer = None
        self.session_csv_log_filehandler = None 
        self.session_csv_log_writer = None
        self.session_json_log_filehandler = None

        if auth_logfile != "":
            # Setup CSV logging for auth attempts
            auth_field_names = ['timestamp', 'auth_id', 'session_id', 'source_ip', 'source_port', 'destination_ip',
                                'destination_port', 'protocol', 'username', 'password']
            
            self.auth_log_filehandler, self.auth_log_writer = self.setup_csv_files(
                auth_logfile, auth_field_names)

            logger.info(
                'File logger: Using %s to log authentication attempts in CSV format.', auth_logfile)

        if session_csv_logfile != "":
            # Setup CSV logging for sessions
            session_field_names = ['timestamp', 'duration', 'session_id', 'source_ip', 'source_port', 'destination_ip',
                                'destination_port', 'protocol', 'num_auth_attempts']
            self.session_csv_log_filehandler, self.session_csv_log_writer = self.setup_csv_files(
                session_csv_logfile, session_field_names)

            logger.info('File logger: Using %s to log unified session data in CSV format.',
                        session_csv_logfile)

        if sessions_json_logfile != "":
            # Setup json logging for logging complete sessions
            if not os.path.isfile(sessions_json_logfile):
                self.session_json_log_filehandler = open(sessions_json_logfile, 'w', encoding='utf-8')
            else:
                self.session_json_log_filehandler = open(sessions_json_logfile, 'a', encoding='utf-8')
            
            logger.info('File logger: Using %s to log complete session data in JSON format.',
                        sessions_json_logfile)

    def setup_csv_files(self, filename, field_names):
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
        for handler in [self.auth_log_filehandler, self.session_csv_log_filehandler, 
                        self.session_json_log_filehandler]:
            if handler != None:
                handler.flush()
                handler.close()

    def handle_auth_log(self, data):
        # for now this logger only handles authentication attempts where we are able
        # to log both username and password
        if self.auth_log_filehandler != None:
            if 'username' in data and 'password' in data:
                self.auth_log_writer.writerow(data)
                # meh
                self.auth_log_filehandler.flush()

    def handle_session_log(self, data):
        if data['session_ended']:
            if self.session_csv_log_filehandler != None:
                self.session_csv_log_writer.writerow(data)
                self.session_csv_log_filehandler.flush()
            if self.session_json_log_filehandler != None:
                self.session_json_log_filehandler.write(json.dumps(data) + "\n")
                self.session_json_log_filehandler.flush()

