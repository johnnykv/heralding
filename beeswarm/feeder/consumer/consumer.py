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
from beeswarm.feeder.consumer.loggers.beekeeper import Beekeeper

class Consumer:
    def __init__(self, sessions, config):
        logging.debug('Consumer created.')
        self.sessions = sessions
        self.config = config
        self.enabled = True
        self.active_loggers = None

    def start_handling(self, sleep_time=5):
        if not self.active_loggers:
            self.active_loggers = self.get_loggers()

        while self.enabled:
            for session_id in self.sessions.keys():
                session = self.sessions[session_id]
                if session.alldone:
                    logging.debug('Found finished honeybee. (bee id: %s)' % session.id)
                    for logger in self.active_loggers:
                        logging.debug(
                            'Logging honeybee with %s (session id: %s)' % (logger.__class__.__name__, session.id))
                        logger.log(session)
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