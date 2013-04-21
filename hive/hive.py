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

import logging
import ConfigParser
import os
import sys
import _socket
import ntplib 

import gevent
from gevent import Greenlet

from consumer import consumer
from capabilities import handlerbase
from models.session import Session
from models.authenticator import Authenticator
from helpers.streamserver import HiveStreamServer
from helpers.common import drop_privileges, list2dict, create_socket

# Do not remove this import, it is required for auto detect.
# See capabilities/__init__.py to see how the auto detect works
import capabilities

logger = logging.getLogger(__name__)


class Hive(object):

    """ This is the main class, which starts up all the capabilities. """

    def __init__(self, config_file='hive.cfg', key='server.key', cert='server.crt'):
        self.key = key
        self.cert = cert

        self.config = ConfigParser.ConfigParser()

        if not os.path.exists(config_file):
            raise ConfigNotFound('Configuration file could not be found. ({0})'.format(config_file))

        self.config.read(config_file)

        #check cert and key
        if not (os.path.isfile(self.key) and os.path.isfile(self.cert)):
            gen_cmd = "openssl req -new -newkey rsa:1024 -days 365 -nodes -x509 -keyout server.key -out server.crt"
            gen_cmd += ' && openssl rsa -in server.key -text -out server.key'
            logger.error('No valid key or certificate found, '
                         'a selfsigned cert and key can be generated with the following '
                         'command: "{0}"'.format(gen_cmd))
            sys.exit(1)

        #inject authentication mechanism
        Session.authenticator = Authenticator({'test': 'test'})

        #spawning time checker
        if self.config.getboolean('timecheck', 'Enabled'):
            Greenlet.spawn(self.checktime)
        
    #function to check the time offset
    def checktime(self):
        """ Make sure our Hive time is consistent, and not too far off
        from the actual time. """

        poll = self.config.getint('timecheck', 'poll')
        ntp_poll = self.config.get('timecheck', 'ntp_pool')
        while True:
            clnt = ntplib.NTPClient()
            response = clnt.request(ntp_poll, version=3)
            diff = response.offset
            if abs(diff) >= 5:
                logger.error('Timings found to be far off. ({0})'.format(diff))
                sys.exit(1)
            gevent.sleep(poll * 60 * 60)

    def start_serving(self):
        """ Starts services. """

        #will contain HiveStreamServer objects
        self.servers = []
        self.server_greenlets = []
        #will contain Session objects
        self.sessions = {}

        self.public_ip = self.config.get('public_ip', 'public_ip')
        self.fetch_ip = self.config.getboolean('public_ip', 'fetch_public_ip')

        #greenlet to consume the provided sessions
        self.session_consumer = consumer.Consumer(self.sessions, public_ip=self.public_ip, fetch_public_ip=self.fetch_ip)
        Greenlet.spawn(self.session_consumer.start)

        #protocol handlers
        for c in handlerbase.HandlerBase.__subclasses__():

            cap_name = 'cap_' + c.__name__

            if not self.config.has_section(cap_name):
                logger.warning(
                    "Not loading {0} capability because it has no option in configuration file.".format(c.__name__))
                continue
                #skip loading if disabled
            if not self.config.getboolean(cap_name, 'Enabled'):
                continue

            port = self.config.getint(cap_name, 'port')
            #carve out the options for this specific service
            options = list2dict(self.config.items(cap_name))
            cap = c(self.sessions, options)

            try:
                socket = create_socket(('0.0.0.0', port))
                #Convention: All capability names which end in 's' will be wrapped in ssl.
                if cap_name.endswith('s'):
                    server = HiveStreamServer(socket, cap.handle_session,
                                              keyfile=self.key, certfile=self.cert)
                else:
                    server = HiveStreamServer(socket, cap.handle_session)

                self.servers.append(server)
                server_greenlet = Greenlet(server.start())
                self.server_greenlets.append(server_greenlet)

            except _socket.error as ex:
                logger.error("Could not start {0} server on port {1}. Error: {2}".format(c.__name__, port, ex))
            else:
                logger.info('Started {0} capability listening on port {1}'.format(c.__name__, port))

        drop_privileges()

        logger.info("Hive running - see log file (hive.log) for attack events.")
        gevent.joinall(self.server_greenlets)

    def stop_serving(self):
        """Stops services"""
        for s in self.servers:
            s.stop()

        for g in self.server_greenlets:
            g.kill()

        self.session_consumer.stop()
        logger.info('All servers stopped.')


class ConfigNotFound(Exception):
    pass
