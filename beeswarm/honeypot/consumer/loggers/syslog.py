# Copyright (C) 2013 Johnny Vestergaard <jkv@unixcluster.dk>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import logging

from beeswarm.honeypot.consumer.loggers.loggerbase import LoggerBase


class Syslog(LoggerBase):
    def __init__(self, config):
        self.options = {
            'enabled': config['log_syslog']['enabled'],
            'socket': config['log_syslog']['socket'],
        }

        #Make sure we only have one logger
        try:
            Syslog.logger
        except AttributeError:
            Syslog.logger = logging.getLogger('beeswarm_auth')
            Syslog.logger.propagate = False
            Syslog.log_handler = logging.handlers.SysLogHandler(address=self.options['socket'])
            Syslog.logger.addHandler(self.log_handler)
            Syslog.logger.setLevel(logging.INFO)

    def log(self, session):

        for attempt in session.login_attempts:
            username = attempt['username']
            password = attempt['password']
            message = 'Beeswarm-Honeypot: Unauthorized {0} logon attempt on port {1}. ' \
                      'Source: {2}:{3}, Username: [{4}], Password: [{5}]. (Session Id: {6})' \
                .format(session.protocol, session.destination_port, session.source_ip,
                        session.source_port, username, password, session.id)
            Syslog.logger.info(message)