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
from beeswarm.hive.consumer.loggers import loggerbase
from beeswarm.hive.consumer.loggers.hpfeedslogger import HPFeedsLogger
from beeswarm.hive.consumer.loggers.beekeeper import Beekeeper

logger = logging.getLogger(__name__)


class Consumer:
    def __init__(self, sessions,  hive_ip, config, status):
        """
            Processes completed/disconnected sessions from the sessions dict.

        :param sessions: The sessions dict, which holds the currently active sessions.
        :param hive_ip: IP Address of the Hive
        :param config: Hive configuration
        :param status: The Hive status dict. This is updated by the consumer.
        """
        logger.debug('Consumer created.')
        self.config = config
        self.enabled = True
        self.hive_ip = hive_ip
        self.status = status
        self.sessions = sessions

    def start(self):
        self.enabled = True

        active_loggers = self.start_loggers(self.get_enabled_loggers())
        
        while self.enabled:
            self.status['active_sessions'] = len(self.sessions)

            for session_id in self.sessions.keys():
                session = self.sessions[session_id]
                if not session.is_connected():
                    for log in active_loggers:
                        session.destination_ip = self.hive_ip
                        try:
                            log.log(session)
                        #make sure this greenlet does not crash on errors while calling loggers
                        except Exception as ex:
                            logger.exception('Error ({0}) while using {1} logger on a {2} session. ({3})'
                                             .format(ex,
                                                     log.__class__.__name__,
                                                     session.protocol,
                                                     session.id))

                    del self.sessions[session_id]
                    self.status['total_sessions'] += 1
                    logger.debug('Removed {0} connection from {1}. ({2})'.format(session.protocol,
                                                                                 session.source_ip,
                                                                                 session.id))
            gevent.sleep(1)
        self.stop_loggers(active_loggers)

    def stop(self):
        self.enabled = False

    def stop_loggers(self, loggers):
        """
        Execute stop method in all logging classes which implement a stop method.

        :param loggers: list of LoggerBase instances.
        """
        for l in loggers:
            stop_method = getattr(l, 'stop', None)
            if callable(stop_method):
                stop_method()

    def get_enabled_loggers(self):
        """
        Extracts names of enabled loggers from configuration file.

        :return: a list of enabled loggers (strings)
        """
        #parser = ConfigParser()
        #parser.read(self.config)
        enabled_loggers = []
        for k, v in self.config.items():
            if '_' in k:
                type, name = k.split('_')
                #only interested in logging configurations
                if type == 'log' and v['enabled']:
                    enabled_loggers.append(name)
        return enabled_loggers

    def start_loggers(self, enabled_logger_classes):
        """
        Starts loggers.

        :param enabled_logger_classes: list of names (string) of loggers to activate.
        :return: a list of instantiated loggers
        """
        loggers = []
        for l in loggerbase.LoggerBase.__subclasses__():
            logger_name = l.__name__.lower()
            if logger_name in enabled_logger_classes:
                hive_logger = l(self.config)
                logger.debug('{0} logger initialized.'.format(logger_name.title()))
                loggers.append(hive_logger)
        return loggers
