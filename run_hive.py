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

import gevent
import gevent.monkey

gevent.monkey.patch_all()
from gevent.server import StreamServer
from gevent import Greenlet

import logging
import os
import pwd
import grp
import ConfigParser
import platform
import sys

from hive.consumer import consumer
from hive.capabilities import handlerbase
from hive.capabilities import pop3
from hive.capabilities import pop3s
from hive.capabilities import telnet
from hive.capabilities import ssh
from hive.capabilities import ftp
from hive.models.session import Session
from hive.models.authenticator import Authenticator

logger = logging.getLogger()


def main():
    config = ConfigParser.ConfigParser()

    if os.path.exists('./hive.cfg'):
        config.read('hive.cfg')
    else:
        logger.error("Config file not found.")
    servers = []
    #shared resource
    sessions = {}
    try:
        public_ip = config.get('public_ip', 'public_ip')
        fetch_ip = config.getboolean('public_ip', 'fetch_public_ip')
    except(ConfigParser.NoSectionError):
        logger.error("Problem parsing config file.")

    #greenlet to consume the provided sessions
    sessions_consumer = consumer.Consumer(sessions, public_ip=public_ip, fetch_public_ip=fetch_ip)
    Greenlet.spawn(sessions_consumer.start_handling)

    #inject authentication mechanism
    Session.authenticator = Authenticator()

    #protocol handlers
    for c in handlerbase.HandlerBase.__subclasses__():
        cap_name = 'cap_' + c.__name__

        #skip loading if no configuration sections is found
        if not config.has_section(cap_name):
            logger.warning(
                "Not loading {0} capability because it has no option in configuration file.".format(c.__name__))
            continue
            #skip loading if disabled
        if not config.getboolean(cap_name, 'Enabled'):
            continue

        port = config.getint(cap_name, 'port')
        cap = c(sessions, port)

        #check cert and key
        if not {'server.key', 'server.crt'}.issubset(set(os.listdir('./'))):
            gen_cmd = "openssl req -new -newkey rsa:1024 -days 365 -nodes -x509 -keyout server.key -out server.crt"
            gen_cmd += ' && openssl rsa -in server.key -text -out server.key'
            logger.error('No valid key or certificate found, '
                         'a selfsigned cert and key can be generated with the following '
                         'command: "{0}"'.format(gen_cmd))
            sys.exit(1)

        #Convention: All capability names which end in 's' will be wrapped in ssl.
        if cap_name.endswith('s'):
                server = StreamServer(('0.0.0.0', port), cap.handle_session,
                                      keyfile='server.key', certfile='server.crt')
        else:
            server = StreamServer(('0.0.0.0', port), cap.handle_session)
            
        servers.append(server)
        try:
            server.start()
        except:
            logger.error("Could not start server. This usually happens when the port specified\
                            in the config file is in use.")
        else:
            logging.debug('Started {0} capability listening on port {1}'.format(c.__name__, port))

    stop_events = []
    for s in servers:
        stop_events.append(s._stopped_event)

    drop_privileges()

    gevent.joinall(stop_events)


def drop_privileges(uid_name='nobody', gid_name='nogroup'):
    if os.getuid() != 0:
        return
        
    wanted_uid = pwd.getpwnam(uid_name)[2]
    #special handling for os x. (getgrname has trouble with gid below 0)
    if platform.mac_ver()[0]:
        wanted_gid = -2
    else:
        wanted_gid = grp.getgrnam(gid_name)[2]

    os.setgid(wanted_gid)

    os.setuid(wanted_uid)

    new_uid_name = pwd.getpwuid(os.getuid())[0]
    new_gid_name = grp.getgrgid(os.getgid())[0]

    logger.info("Privileges dropped, running as {0}/{1}.".format(new_uid_name, new_gid_name))


if __name__ == '__main__':

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)-15s (%(name)s) %(message)s')
    console_log = logging.StreamHandler()
    console_log.setLevel(logging.INFO)
    console_log.setFormatter(formatter)
    root_logger.addHandler(console_log)
    file_log = logging.FileHandler(
        'hive.log')
    file_log.setLevel(logging.DEBUG)
    file_log.setFormatter(formatter)
    root_logger.addHandler(file_log)
    main()
