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

from gevent.server import StreamServer
from gevent import Greenlet
import logging
import os
import gevent

from hive.consumer import consumer
from hive.capabilities import handlerbase
from hive.capabilities import pop3
from hive.capabilities import pop3s
from hive.capabilities import telnet
from hive.models.session import Session
from hive.models.authenticator import Authenticator

logger = logging.getLogger()


def main():
    servers = []
    #shared resource
    sessions = {}

    #greenlet to consume the provided sessions
    sessions_consumer = consumer.Consumer(sessions)
    Greenlet.spawn(sessions_consumer.start_handling)

    #inject authentication mechanism
    Session.authenticator = Authenticator()

    #protocol handlers
    for c in handlerbase.HandlerBase.__subclasses__():
        cap = c(sessions)
        cap_name = cap.__class__.__name__
        #Convention: All capability names which end in 's' will be wrapped in ssl.
        if cap_name.endswith('s'):
            if not {'server.key', 'server.crt'}.issubset(set(os.listdir('./'))):
                gen_cmd = "openssl req -new -newkey rsa:2048 -days 365 -nodes -x509 -keyout server.key -out server.crt"
                logger.error('{0} could not be activated because no SSL cert was found, '
                             'a selfsigned cert kan be generated with the following '
                             'command: "{1}"'.format(cap_name, gen_cmd))
            else:
                server = StreamServer(('0.0.0.0', cap.get_port()), cap.handle,
                                      keyfile='server.key', certfile='server.crt')
            pass
        else:
            server = StreamServer(('0.0.0.0', cap.get_port()), cap.handle)
        servers.append(server)
        server.start()
        logging.debug('Started {0} capability listening on port {1}'.format(cap_name , cap.get_port()))

    stop_events = []
    for s in servers:
        stop_events.append(s._stopped_event)

    gevent.joinall(stop_events)


if __name__ == '__main__':
    format_string = '%(asctime)-15s (%(name)s) %(message)s'
    logging.basicConfig(level=logging.DEBUG, format=format_string)
    main()