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
from datetime import datetime, timedelta
from gevent import Greenlet

import zmq.green as zmq
import gevent
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import func

import beeswarm
import beeswarm.shared
from beeswarm.server.db import database_setup
from beeswarm.server.db.entities import Client, BaitSession, Session, Honeypot, Authentication, Classification, \
    Transcript
from beeswarm.shared.helpers import send_zmq_request_socket
from beeswarm.shared.message_enum import Messages
from beeswarm.shared.socket_enum import SocketNames

logger = logging.getLogger(__name__)


class SessionPersister(gevent.Greenlet):
    def __init__(self, max_sessions, clear_sessions=False):
        Greenlet.__init__(self)
        self.db_session = database_setup.get_session()
        # clear all pending sessions on startup, pending sessions on startup
        pending_classification = self.db_session.query(Classification).filter(Classification.type == 'pending').one()
        pending_deleted = self.db_session.query(Session).filter(
            Session.classification == pending_classification).delete()
        self.db_session.commit()
        logging.info('Cleaned {0} pending sessions on startup'.format(pending_deleted))
        self.do_classify = False
        if clear_sessions or max_sessions == 0:
            count = self.db_session.query(Session).delete()
            logging.info('Deleting {0} sessions on startup.'.format(count))
            self.db_session.commit()

        self.max_session_count = max_sessions
        if max_sessions:
            logger.info('Database has been limited to contain {0} sessions.'.format(max_sessions))

        context = beeswarm.shared.zmq_context
        self.subscriber_sessions = context.socket(zmq.SUB)
        self.subscriber_sessions.connect(SocketNames.RAW_SESSIONS)
        self.subscriber_sessions.setsockopt(zmq.SUBSCRIBE, Messages.SESSION_CLIENT)
        self.subscriber_sessions.setsockopt(zmq.SUBSCRIBE, Messages.SESSION_HONEYPOT)

        self.processedSessionsPublisher = context.socket(zmq.PUB)
        self.processedSessionsPublisher.bind(SocketNames.PROCESSED_SESSIONS)

        self.config_actor_socket = context.socket(zmq.REQ)
        self.config_actor_socket.connect(SocketNames.CONFIG_COMMANDS)

    def _run(self):
        poller = zmq.Poller()
        poller.register(self.subscriber_sessions, zmq.POLLIN)
        gevent.spawn(self._start_recurring_classify_set)
        while True:
            # .recv() gives no context switch - why not? using poller with timeout instead
            socks = dict(poller.poll(100))
            gevent.sleep()
            if self.do_classify:
                self.classify_malicious_sessions()
                self.do_classify = False
            elif self.subscriber_sessions in socks and socks[self.subscriber_sessions] == zmq.POLLIN:
                data = self.subscriber_sessions.recv()
                topic, honeypot_id, session_json = data.split(' ', 2)
                self.persist_session(session_json, topic)

    def _start_recurring_classify_set(self):
        while True:
            gevent.sleep(20)
            self.do_classify = True

    def persist_session(self, session_json, session_type):
        db_session = self.db_session

        if self.max_session_count == 0:
            return
        elif db_session.query(Session).count() == self.max_session_count:
            session_to_delete = db_session.query(Session, func.min(Session.timestamp)).first()[0]
            db_session.delete(session_to_delete)

        try:
            data = json.loads(session_json)
        except UnicodeDecodeError:
            data = json.loads(unicode(session_json, "ISO-8859-1"))
        logger.debug('Persisting {0} session: {1}'.format(session_type, data))

        db_session = self.db_session
        classification = db_session.query(Classification).filter(Classification.type == 'pending').one()

        assert data['honeypot_id'] is not None
        _honeypot = db_session.query(Honeypot).filter(Honeypot.id == data['honeypot_id']).one()

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
                logger.debug('Ignore failed bait session.')
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

        matching_session = self.get_matching_session(session, db_session)
        if session_type == Messages.SESSION_HONEYPOT:
            if matching_session:
                self.merge_bait_and_session(session, matching_session, db_session)
        elif session_type == Messages.SESSION_CLIENT:
            if matching_session:
                self.merge_bait_and_session(matching_session, session, db_session)
        else:
            assert False

    def extract_auth_entity(self, auth_data):
        username = auth_data.get('username', '')
        password = auth_data.get('password', '')
        authentication = Authentication(id=auth_data['id'], username=username, password=password,
                                        successful=auth_data['successful'],
                                        timestamp=datetime.strptime(auth_data['timestamp'], '%Y-%m-%dT%H:%M:%S.%f'))
        return authentication

    def get_matching_session(self, session, db_session, timediff=5):
        """
        Tries to match a session with it's counterpart. For bait session it will try to match it with honeypot sessions
        and the other way around.

        :param session: session object which will be used as base for query.
        :param timediff: +/- allowed time difference between a session and a potential matching session.
        """
        db_session = db_session
        min_datetime = session.timestamp - timedelta(seconds=timediff)
        max_datetime = session.timestamp + timedelta(seconds=timediff)

        # default return value
        match = None
        classification = db_session.query(Classification).filter(Classification.type == 'pending').one()
        # get all sessions that match basic properties.
        sessions = db_session.query(Session).options(joinedload(Session.authentication)) \
            .filter(Session.protocol == session.protocol) \
            .filter(Session.honeypot == session.honeypot) \
            .filter(Session.timestamp >= min_datetime) \
            .filter(Session.timestamp <= max_datetime) \
            .filter(Session.id != session.id) \
            .filter(Session.classification == classification)

        # identify the correct session by comparing authentication.
        # this could properly also be done using some fancy ORM/SQL construct.
        for potential_match in sessions:
            assert potential_match.id != session.id
            for honey_auth in session.authentication:
                for session_auth in potential_match.authentication:
                    if session_auth.username == honey_auth.username and \
                                    session_auth.password == honey_auth.password and \
                                    session_auth.successful == honey_auth.successful:
                        assert potential_match.id != session.id
                        match = potential_match
                        break

        return match

    def merge_bait_and_session(self, honeypot_session, bait_session, db_session):
        logger.debug('Classifying bait session with id {0} as legit bait and deleting '
                     'matching honeypot_session with id {1}'.format(bait_session.id, honeypot_session.id))
        bait_session.classification = db_session.query(Classification).filter(
            Classification.type == 'bait_session').one()
        bait_session.transcript = honeypot_session.transcript
        bait_session.session_data = honeypot_session.session_data
        # the client ip own detection can be flawed, but we are sure the the honeypot tcp source ip
        # is the same as the clients source ip.
        bait_session.source_ip = honeypot_session.source_ip
        db_session.add(bait_session)
        db_session.delete(honeypot_session)
        db_session.commit()
        self.processedSessionsPublisher.send('{0} {1} {2}'.format(Messages.DELETED_DUE_TO_MERGE, honeypot_session.id,
                                                                  bait_session.id))
        self.processedSessionsPublisher.send('{0} {1}'.format(Messages.SESSION,
                                                              json.dumps(bait_session.to_dict())))

    def classify_malicious_sessions(self, delay_seconds=30):
        """
        Will classify all unclassified sessions as malicious activity.

        :param delay_seconds: no sessions newer than (now - delay_seconds) will be processed.
        """
        min_datetime = datetime.utcnow() - timedelta(seconds=delay_seconds)

        db_session = self.db_session

        # find and process bait sessions that did not get classified during persistence.
        bait_sessions = db_session.query(BaitSession).options(joinedload(BaitSession.authentication)) \
            .filter(BaitSession.classification_id == 'pending') \
            .filter(BaitSession.did_complete == True) \
            .filter(BaitSession.received < min_datetime).all()

        for bait_session in bait_sessions:
            logger.debug('Classifying bait session with id {0} as MITM'.format(bait_session.id))
            bait_session.classification = db_session.query(Classification).filter(Classification.type == 'mitm').one()

        # find and process honeypot sessions that did not get classified during persistence.
        sessions = db_session.query(Session).filter(Session.discriminator == None) \
            .filter(Session.timestamp <= min_datetime) \
            .filter(Session.classification_id == 'pending') \
            .all()

        for session in sessions:
            # Check if the attack used credentials leaked by beeswarm drones
            bait_match = None
            for a in session.authentication:
                bait_match = db_session.query(BaitSession) \
                    .filter(BaitSession.authentication.any(username=a.username, password=a.password)).first()
                if bait_match:
                    break

            if bait_match:
                logger.debug('Classifying session with id {0} as attack which involved the reuse '
                             'of previously transmitted credentials.'.format(session.id))
                session.classification = db_session.query(Classification).filter(
                    Classification.type == 'credentials_reuse').one()
            elif len(session.authentication) == 0:
                logger.debug('Classifying session with id {0} as probe.'.format(session.id))
                session.classification = db_session.query(Classification).filter(Classification.type == 'probe').one()
            else:
                # we have never transmitted this username/password combo
                logger.debug('Classifying session with id {0} as bruteforce attempt.'.format(session.id))
                session.classification = db_session.query(Classification).filter(
                    Classification.type == 'bruteforce').one()
            db_session.commit()
            self.processedSessionsPublisher.send('{0} {1}'.format(Messages.SESSION, json.dumps(session.to_dict())))

    def send_config_request(self, request):
        return send_zmq_request_socket(self.config_actor_socket, request)



