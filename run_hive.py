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
import gevent

from hive.consumer import consumer
from hive.capabilities import handlerbase
from hive.capabilities import pop3
from hive.capabilities import telnet


def main():
    servers = []
    sessions = {}
    accounts = {'test': 'test'}

    #greenlet to consume and maintain data in sessions list
    sessions_consumer = consumer.Consumer(sessions)
    Greenlet.spawn(sessions_consumer.start_handling)

    #protocol handlers
    for c in handlerbase.HandlerBase.__subclasses__():
        cap = c(sessions, accounts)
        server = StreamServer(('0.0.0.0', cap.get_port()), cap.handle)
        servers.append(server)
        server.start()
        logging.debug('Started {0} capability listening on port {1}'.format( cap.__class__.__name__, cap.get_port()))

    stop_events = []
    for s in servers:
        stop_events.append(s._stopped_event)

    gevent.joinall(stop_events)


if __name__ == '__main__':
    format_string = '%(asctime)-15s (%(name)s) %(message)s'
    logging.basicConfig(level=logging.DEBUG, format=format_string)
    main()