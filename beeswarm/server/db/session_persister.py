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
from gevent import Greenlet

import beeswarm
import beeswarm.shared
from beeswarm.server.db import database_setup
from beeswarm.server.db.entities import Client, BaitSession, Session, Honeypot, Authentication, Classification, \
    Transcript
from beeswarm.shared.helpers import send_zmq_request_socket
from beeswarm.shared.message_enum import Messages


logger = logging.getLogger(__name__)


class SessionPersister(gevent.Greenlet):
    def __init__(self, clear_sessions=False):
        Greenlet.__init__(self)
        db_session = database_setup.get_session()
        # clear all pending sessions on startup, pending sessions on startup
        pending_classification = db_session.query(Classification).filter(Classification.type == 'pending').one()
        pending_deleted = db_session.query(Session).filter(Session.classification == pending_classification).delete()
        db_session.commit()
        logging.info('Cleaned {0} pending sessions on startup'.format(pending_deleted))
        if clear_sessions:
            count = db_session.query(Session).delete()
            logging.info('Deleting {0} sessions on startup.'.format(count))
            db_session.commit()
        context = beeswarm.shared.zmq_context
        self.subscriber_sessions = context.socket(zmq.SUB)
        self.subscriber_sessions.connect('inproc://sessionPublisher')
        self.subscriber_sessions.setsockopt(zmq.SUBSCRIBE, '')

        self.config_actor_socket = context.socket(zmq.REQ)
        self.config_actor_socket.connect('inproc://configCommands')

    def _run(self):
        poller = zmq.Poller()
        poller.register(self.subscriber_sessions, zmq.POLLIN)
        while True:
            # .recv() gives no context switch - why not? using poller with timeout instead
            socks = dict(poller.poll(100))
            gevent.sleep()

            if self.subscriber_sessions in socks and socks[self.subscriber_sessions] == zmq.POLLIN:
                topic, session_json = self.subscriber_sessions.recv().split(' ', 1)
                logger.debug('Received message from publisher')
                self.persist_session(session_json, topic)

    def persist_session(self, session_json, session_type):
        data = json.loads(session_json)
        logger.debug('Persisting {0} session: {1}'.format(session_type, data))
        db_session = database_setup.get_session()
        classification = db_session.query(Classification).filter(Classification.type == 'pending').one()
        if data['honeypot_id'] is not None:
            _honeypot = db_session.query(Honeypot).filter(Honeypot.id == data['honeypot_id']).one()
        else:
            _honeypot = None

        if session_type == Messages.SESSION_HONEYPOT:
            session = Session()
            for entry in data['transcript']:
                transcript_timestamp = datetime.strptime(entry['timestamp'], '%Y-%m-%dT%H:%M:%S.%f')
                transcript = Transcript(timestamp=transcript_timestamp, direction=entry['direction'],
                                        data=entry['data'])
                session.transcript.append(transcript)

            for auth in data['login_attempts']:
                authentication = self.extract_auth_entity(auth)
                session.authentication.append(authentication)

        elif session_type == Messages.SESSION_CLIENT:
            ignore_failed_bait_sessions = self.send_config_request('{0} {1}'.format(Messages.GET_CONFIG_ITEM,
                                                                                    'ignore_failed_bait_session'))
            if not data['did_complete'] and ignore_failed_bait_sessions:
                return
            session = BaitSession()
            client = db_session.query(Client).filter(Client.id == data['client_id']).one()
            client.last_activity = datetime.now()
            session.did_connect = data['did_connect']
            session.did_login = data['did_login']
            session.did_complete = data['did_complete']
            session.client = client
            for auth in data['login_attempts']:
                authentication = self.extract_auth_entity(auth)
                session.authentication.append(authentication)
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

    def extract_auth_entity(self, auth_data):
        username = auth_data.get('username', '')
        password = auth_data.get('password', '')
        authentication = Authentication(id=auth_data['id'], username=username, password=password,
                                        successful=auth_data['successful'],
                                        timestamp=datetime.strptime(auth_data['timestamp'], '%Y-%m-%dT%H:%M:%S.%f'))
        return authentication

    def send_config_request(self, request):
            return send_zmq_request_socket(self.config_actor_socket, request)



