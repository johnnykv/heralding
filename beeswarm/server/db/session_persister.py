# Copyright (C) 2014 Johnny Vestergaard <jkv@unixcluster.dk>
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

import json
import logging
from datetime import datetime

import zmq.green as zmq
import gevent

from beeswarm.server.db import database_setup
from beeswarm.server.db.entities import Client, Honeybee, Session, Honeypot, Authentication, Classification, \
    Transcript


logger = logging.getLogger(__name__)


class PersistanceWorker(object):
    def __init__(self):
        ctx = zmq.Context()
        self.subscriber_socket = ctx.socket(zmq.SUB)
        self.subscriber_socket.connect('ipc://sessionPublisher')
        self.subscriber_socket.setsockopt(zmq.SUBSCRIBE, 'session')
        self.first_cfg_received = gevent.event.Event()
        self.config = None

    def config_subscriber(self):
        global config
        ctx = zmq.Context()
        subscriber_socket = ctx.socket(zmq.SUB)
        subscriber_socket.connect('ipc://configPublisher')
        subscriber_socket.setsockopt(zmq.SUBSCRIBE, 'full')
        while True:
            poller = zmq.Poller()
            poller.register(subscriber_socket, zmq.POLLIN)
            while True:
                socks = dict(poller.poll())
                if subscriber_socket in socks and socks[subscriber_socket] == zmq.POLLIN:
                    topic, msg = subscriber_socket.recv().split(' ', 1)
                    self.config = json.loads(msg)
                    self.first_cfg_received.set()
                    logger.debug('Config received')

    def start(self):
        gevent.spawn(self.config_subscriber)
        # we cannot proceede before we have received a initial configuration message
        self.first_cfg_received.wait()
        while True:
            topic, session_json = self.subscriber_socket.recv().split(' ', 1)
            logger.debug('Received message from publisher')
            self.persist_session(session_json, topic)

    def persist_session(self, session_json, session_type):
        data = json.loads(session_json)
        db_session = database_setup.get_session()
        classification = db_session.query(Classification).filter(Classification.type == 'unclassified').one()
        if data['honeypot_id'] is not None:
            _honeypot = db_session.query(Honeypot).filter(Honeypot.id == data['honeypot_id']).one()
        else:
            _honeypot = None

        if session_type == 'session_honeypot':
            session = Session()
            for entry in data['transcript']:
                transcript_timestamp = datetime.strptime(entry['timestamp'], '%Y-%m-%dT%H:%M:%S.%f')
                transcript = Transcript(timestamp=transcript_timestamp, direction=entry['direction'],
                                        data=entry['data'])
                session.transcript.append(transcript)

            for auth in data['login_attempts']:
                # TODO: Model this better in db model, not all capabilities authenticate with both username/password
                username = auth.get('username', '')
                password = auth.get('password', '')
                a = Authentication(id=auth['id'], username=username, password=password,
                                   successful=auth['successful'],
                                   timestamp=datetime.strptime(auth['timestamp'], '%Y-%m-%dT%H:%M:%S.%f'))
                session.authentication.append(a)
        elif session_type == 'session_client':
            if not data['did_complete'] and self.config['ignore_failed_honeybees']:
                return
            session = Honeybee()
            client = db_session.query(Client).filter(Client.id == data['client_id']).one()
            session.did_connect = data['did_connect']
            session.did_login = data['did_login']
            session.did_complete = data['did_complete']
            session.client = client
        else:
            logger.warn('Unknown message type: {0}'.format(session_type))
            return

        session.id = data['id']
        session.classification = classification
        session.timestamp = datetime.strptime(data['timestamp'], '%Y-%m-%dT%H:%M:%S.%f')
        session.received = datetime.utcnow()
        session.protocol = data['protocol']
        session.destination_ip = data['destination_ip']
        session.destination_port = data['destination_port']
        session.source_ip = data['source_ip']
        session.source_port = data['source_port']
        session.honeypot = _honeypot

        db_session.add(session)
        db_session.commit()

