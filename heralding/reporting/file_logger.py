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
import heralding

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

        logger.info('File logger: Using %s to log session data.', session_logfile)
        logger.info('File logger: Using %s to log authentication attempts.', session_logfile)


        self.aux_data_fields = {
            'ssh': heralding.capabilities.ssh.SSH.get_aux_fields(),
            'http': heralding.capabilities.http.HTTPHandler.get_aux_fields(),
            'telnet': heralding.capabilities.telnet.TelnetWrapper.get_aux_fields(),
        }

        # store all the auxiliary handlers and writers in a dict
        self.aux_handlers_writers = {}
        for p in self.aux_data_fields:
            logger.info('File logger: Using %s to log auxiliary data from %s sessions.', self.get_auxiliary_logfile_name(p), p)
            self.aux_handlers_writers[p] = self.setup_file(
                self.get_auxiliary_logfile_name(p), self.get_filelog_fields(p))

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
        if data['session_ended']:
            self.session_log_writer.writerow(data)
            # double meh
            self.session_log_filehandler.flush()

    def handle_auxiliary_log(self, data):
        handler, writer = self.aux_handlers_writers.get(data['protocol'], (None, None))
        if handler and writer:
            writer.writerow(data)
            handler.flush()

    def get_auxiliary_logfile_name(self,protocol_name):
        return 'log_auxiliary_'+protocol_name+'.csv'

    def get_filelog_fields(self,protocol_name):
        default_fields = ['timestamp', 'session_id', 'protocol']
        protocol_fields = self.aux_data_fields.get(protocol_name)
        return default_fields+protocol_fields
