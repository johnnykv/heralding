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

import logging

import gevent

from beeswarm.shared.misc.server_logger import ServerLogger
from beeswarm.shared.message_enum import Messages

logger = logging.getLogger(__name__)


class Consumer:
    def __init__(self, sessions, honeypot_ip, config):
        """
            Processes completed/disconnected sessions from the sessions dict.

        :param sessions: The sessions dict, which holds the currently active sessions.
        :param honeypot_ip: IP Address of the Honeypot
        :param config: Honeypot configuration
        :param status: The Honeypot status dict. This is updated by the consumer.
        """
        logger.debug('Consumer created.')
        self.config = config
        self.enabled = True
        self.honeypot_ip = honeypot_ip
        self.sessions = sessions
        self.logger = ServerLogger(Messages.SESSION_HONEYPOT)

    def start(self):
        self.enabled = True
        while self.enabled:
            for session_id in self.sessions.keys():
                session = self.sessions[session_id]
                if not session.is_connected():
                    self.logger.log(session)
                    del self.sessions[session_id]
                    logger.debug('Removed {0} connection from {1}. ({2})'.format(session.protocol,
                                                                                 session.source_ip,
                                                                                 session.id))
            gevent.sleep(1)

    def stop(self):
        self.enabled = False