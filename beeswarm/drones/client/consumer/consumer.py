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


class Consumer(object):
    def __init__(self, sessions, config, own_ip):
        """
            Processes completed sessions from the sessions dict.

        :param sessions: The sessions dict, which holds the currently active sessions.
        :param config: The Client configuration.
        :param status: The Client status dict. This is updated by the consumer.
        """
        logger.debug('Consumer created.')
        self.sessions = sessions
        self.config = config
        self.enabled = True
        self.logger = ServerLogger(Messages.SESSION_CLIENT)
        self.own_ip = own_ip

    def start_handling(self, sleep_time=1):
        while self.enabled:
            for session_id in self.sessions.keys():
                session = self.sessions[session_id]
                if session.alldone:
                    logger.debug('Found finished {0} bait session. (bait id: {1})'.format(session.protocol, session.id))
                    session.source_ip = self.own_ip
                    self.logger.log(session)
                    del self.sessions[session_id]
            gevent.sleep(sleep_time)

    def stop_handling(self):
        self.enabled = False