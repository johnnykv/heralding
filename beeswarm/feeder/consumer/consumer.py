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
from beeswarm.feeder.consumer.loggers import loggerbase

logger = logging.getLogger(__name__)


class Consumer:
    def __init__(self, sessions, config, status):
        """
            Processes completed sessions from the sessions dict.

        :param sessions: The sessions dict, which holds the currently active sessions.
        :param config: The Feeder configuration.
        :param status: The Feeder status dict. This is updated by the consumer.
        """
        logger.debug('Consumer created.')
        self.sessions = sessions
        self.config = config
        self.status = status
        self.enabled = True
        self.active_loggers = None

    def start_handling(self, sleep_time=5):
        if not self.active_loggers:
            self.active_loggers = self.get_loggers()

        while self.enabled:
            self.status['active_bees'] = len(self.sessions)
            for session_id in self.sessions.keys():
                session = self.sessions[session_id]
                if session.alldone:
                    logger.debug('Found finished honeybee. (bee id: %s)' % session.id)
                    for _logger in self.active_loggers:
                        logger.debug(
                            'Logging honeybee with %s (session id: %s)' % (logger.__class__.__name__, session.id))
                        _logger.log(session)
                    self.status['total_bees'] += 1
                    del self.sessions[session_id]
            gevent.sleep(sleep_time)

    def stop_handling(self):
        self.enabled = False

    def get_loggers(self):
        loggers = []
        for l in loggerbase.LoggerBase.__subclasses__():
            if self.config['log_' + l.__name__.lower()]['enabled']:
                logger = l(self.config)
                loggers.append(logger)
        return loggers
