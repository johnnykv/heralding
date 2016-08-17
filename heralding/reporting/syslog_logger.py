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

import syslog
import logging
from base_logger import BaseLogger

logger = logging.getLogger(__name__)


class SyslogLogger(BaseLogger):
    def __init__(self):
        super(SyslogLogger, self).__init__()
        logger.debug('Syslog logger started')


    def handle_log_data(self, data):
        message = "Authentication from {0}:{1}, with username: {2} and password: {3}.".format(
        data['source_ip'], data['source_port'], data['username'], data['password'])
        syslog.syslog(syslog.LOG_ALERT, message)
