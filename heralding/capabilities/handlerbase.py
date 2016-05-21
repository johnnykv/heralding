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

import logging
import socket

from gevent.timeout import Timeout

from heralding.misc.session import Session

logger = logging.getLogger(__name__)


class HandlerBase(object):
    MAX_GLOBAL_SESSIONS = 800
    global_sessions = 0

    def __init__(self, options):
        """
        Base class that all capabilities must inherit from.

        :param sessions: a dictionary of Session objects.
        :param options: a dictionary of configuration options.
        """
        self.options = options
        self.sessions = {}
        self.users = {}

        self.port = int(options['port'])
        if 'timeout' in options:
            self.timeout = options['timeout']
        else:
            self.timeout = 30

    def create_session(self, address):
        protocol = self.__class__.__name__.lower()
        session = Session(address[0], address[1], protocol, self.users)
        self.sessions[session.id] = session
        HandlerBase.global_sessions += 1
        session.destination_port = self.port
        logger.debug(
            'Accepted {0} session on port {1} from {2}:{3}. ({4})'.format(protocol, self.port, address[0],
                                                                          address[1], str(session.id)))
        logger.debug('Size of session list for {0}: {1}'.format(protocol, len(self.sessions)))
        return session

    def close_session(self, session):
        logger.debug('Closing session. ({0})'.format(str(session.id)))
        session.end_session()
        if session.id in self.sessions:
            del self.sessions[session.id]
        else:
            assert False
        HandlerBase.global_sessions -= 1

    def execute_capability(self, address, gsocket, session):
        address = None  # NOQA
        gsocket = None  # NOQA
        session = None  # NOQA
        raise Exception("Must be implemented by child")

    def handle_session(self, gsocket, address):
        if HandlerBase.global_sessions > HandlerBase.MAX_GLOBAL_SESSIONS:
            protocol = self.__class__.__name__.lower()
            logger.warning(
                'Got {0} session on port {1} from {2}:{3}, but not handling it because the global session limit has '
                'been reached'.format(protocol, self.port, address[0], address[1]))
        else:
            session = self.create_session(address)
            try:
                with Timeout(self.timeout):
                    self.execute_capability(address, gsocket, session)
            except socket.error as err:
                logger.debug('Unexpected end of session: {0}, errno: {1}. ({2})'.format(err, err.errno, session.id))
            except Timeout:
                logger.debug('Session timed out. ({0})'.format(session.id))
            finally:
                self.close_session(session)
                try:
                    gsocket.close()
                except:
                    pass
