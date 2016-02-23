# Copyright (C) 2013 Johnny Vestergaard <jkv@unixcluster.dk>
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

import _socket
import logging
import os


import gevent
import requests
from gevent import Greenlet
from gevent.server import StreamServer
from requests.exceptions import Timeout, ConnectionError

from heralding.capabilities import handlerbase

logger = logging.getLogger(__name__)


class Honeypot(object):
    """ This is the main class, which starts up all capabilities. """
    def __init__(self, config, key='server.key', cert='server.crt'):
        """
            Main class which runs Beeswarm in Honeypot mode.

        :param config: Beeswarm configuration dictionary, None if no configuration was supplied.
        :param key: Key file used for SSL enabled capabilities
        :param cert: Cert file used for SSL enabled capabilities
        """

        self.config = config
        self._servers = []
        self._server_greenlets = []

        self.honeypot_ip = ''

    def start(self):
        """ Starts services. """

        # protocol handlers
        for c in handlerbase.HandlerBase.__subclasses__():

            cap_name = c.__name__.lower()

            if cap_name in self.config['capabilities']:
                if not self.config['capabilities'][cap_name]['enabled']:
                    continue
                port = self.config['capabilities'][cap_name]['port']
                # carve out the options for this specific service
                options = self.config['capabilities'][cap_name]
                # capabilities are only allowed to append to the session list
                cap = c(options)

                try:
                    # Convention: All capability names which end in 's' will be wrapped in ssl.
                    if cap_name.endswith('s'):
                        server = StreamServer(('0.0.0.0', port), cap.handle_session,
                                              keyfile=self.key, certfile=self.cert)
                    else:
                        server = StreamServer(('0.0.0.0', port), cap.handle_session)

                    logger.debug('Adding {0} capability with options: {1}'.format(cap_name, options))
                    self._servers.append(server)
                    server_greenlet = Greenlet(server.start())
                    self._server_greenlets.append(server_greenlet)

                except _socket.error as ex:
                    logger.error("Could not start {0} server on port {1}. Error: {2}".format(c.__name__, port, ex))
                else:
                    logger.info('Started {0} capability listening on port {1}'.format(c.__name__, port))

        logger.info("Honeypot running.")

        gevent.joinall(self._server_greenlets)

    def stop(self):
        """Stops services"""

        for s in self._servers:
            s.stop()

        for g in self._server_greenlets:
            g.kill()

        logger.info('All workers stopped.')
