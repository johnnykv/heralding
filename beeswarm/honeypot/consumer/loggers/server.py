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
import urlparse
import uuid
import json
import tempfile
import os
from datetime import datetime


import gevent
import zmq.green as zmq
import zmq.auth
from zmq.utils.monitor import recv_monitor_message
from beeswarm.honeypot.consumer.loggers.loggerbase import LoggerBase

logger = logging.getLogger(__name__)


class Server(LoggerBase):
    def __init__(self, config, work_dir):
        super(Server, self).__init__(config, work_dir)
        context = zmq.Context()
        self.push_socket = context.socket(zmq.PUSH)

        cert_path = os.path.join(self.work_dir, 'certificates')
        public_keys_dir = os.path.join(cert_path, 'public_keys')
        private_keys_dir = os.path.join(cert_path, 'private_keys')

        client_secret_file = os.path.join(private_keys_dir, "client.key")
        client_public, client_secret = zmq.auth.load_certificate(client_secret_file)

        self.push_socket.curve_secretkey = client_secret
        self.push_socket.curve_publickey = client_public

        server_public_file = os.path.join(public_keys_dir, "server.key")
        server_public, _ = zmq.auth.load_certificate(server_public_file)

        self.push_socket.curve_serverkey = server_public
        self.reconnect_interval = 2000
        self.push_socket.setsockopt(zmq.RECONNECT_IVL, self.reconnect_interval)
        self.monitor_socket = self.push_socket.get_monitor_socket()
        self.monitor_socket.linger = 0
        gevent.spawn(self.monitor_worker)
        self.push_socket.connect(config['beeswarm_server']['zmq_url'])

    def log(self, session):
        data = json.dumps(session.to_dict(), default=json_default)
        er = self.push_socket.send('{0} {1}'.format('session_honeypot', data))
        print 'ERROR: {0}'.format(er)

    def monitor_worker(self):
        poller = zmq.Poller()
        poller.register(self.monitor_socket, zmq.POLLIN)
        while True:
            socks = poller.poll(0)
            if len(socks) > 0:
                data = recv_monitor_message(self.monitor_socket)
                event = data['event']
                value = data['value']
                if event == zmq.EVENT_CONNECTED:
                    logger.info('Connected to Beeswarm server')
                elif event == zmq.EVENT_DISCONNECTED:
                    logger.warning('Disconnected from Beeswarm server, will reconnect in {0} seconds.'.format(self.reconnect_interval))
            gevent.sleep()


def json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, uuid.UUID):
        return str(obj)
    else:
        return None
