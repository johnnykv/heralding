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
import random
from datetime import datetime, timedelta

from gevent import Greenlet
import zmq.green as zmq
import gevent
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.expression import func

import beeswarm
import beeswarm.shared
from beeswarm.server.db import database_setup
from beeswarm.server.db.entities import BaitSession, Session, Client, Authentication, Classification, \
    Transcript, Honeypot, Drone, DroneEdge, BaitUser
from beeswarm.shared.helpers import send_zmq_request_socket
from beeswarm.shared.message_enum import Messages
from beeswarm.shared.socket_enum import SocketNames


logger = logging.getLogger(__name__)


class DatabaseActor(gevent.Greenlet):
    def __init__(self, max_sessions, clear_sessions=False, delay_seconds=30):
        assert delay_seconds > 1
        Greenlet.__init__(self)
        db_session = database_setup.get_session()
        # pending session will be converted to attacks if we cannot match with bait traffic
        # with this period
        self.delay_seconds = delay_seconds
        # clear all pending sessions on startup, pending sessions on startup
        pending_classification = db_session.query(Classification).filter(Classification.type == 'pending').one()
        pending_deleted = db_session.query(Session).filter(
            Session.classification == pending_classification).delete()
        db_session.commit()
        logging.info('Cleaned {0} pending sessions on startup'.format(pending_deleted))
        self.do_classify = False
        if clear_sessions or max_sessions == 0:
            db_session = database_setup.get_session()
            count = db_session.query(Session).delete()
            logging.info('Deleting {0} sessions on startup.'.format(count))
            db_session.commit()

        self.max_session_count = max_sessions
        if max_sessions:
            logger.info('Database has been limited to contain {0} sessions.'.format(max_sessions))

        context = beeswarm.shared.zmq_context

        self.subscriber_sessions = context.socket(zmq.SUB)
        self.subscriber_sessions.connect(SocketNames.RAW_SESSIONS.value)
        self.subscriber_sessions.setsockopt(zmq.SUBSCRIBE, Messages.SESSION_CLIENT.value)
        self.subscriber_sessions.setsockopt(zmq.SUBSCRIBE, Messages.SESSION_HONEYPOT.value)

        self.processedSessionsPublisher = context.socket(zmq.PUB)
        self.processedSessionsPublisher.bind(SocketNames.PROCESSED_SESSIONS.value)

        self.databaseRequests = context.socket(zmq.REP)
        self.databaseRequests.bind(SocketNames.DATABASE_REQUESTS.value)

        self.config_actor_socket = context.socket(zmq.REQ)
        self.config_actor_socket.connect(SocketNames.CONFIG_COMMANDS.value)

    def _run(self):
        poller = zmq.Poller()
        poller.register(self.subscriber_sessions, zmq.POLLIN)
        poller.register(self.databaseRequests, zmq.POLLIN)
        gevent.spawn(self._start_recurring_classify_set)
        while True:
            # .recv() gives no context switch - why not? using poller with timeout instead
            socks = dict(poller.poll(100))
            gevent.sleep()
            if self.do_classify:
                logger.debug('Doing classify')
                self.classify_malicious_sessions()
                self.do_classify = False
            elif self.subscriber_sessions in socks and socks[self.subscriber_sessions] == zmq.POLLIN:
                data = self.subscriber_sessions.recv()
                topic, honeypot_id, session_json = data.split(' ', 2)
                self.persist_session(session_json, topic)
            elif self.databaseRequests in socks and socks[self.databaseRequests] == zmq.POLLIN:
                data = self.databaseRequests.recv()
                if ' ' in data:
                    cmd, data = data.split(' ', 1)
                else:
                    cmd = data

                if cmd == Messages.DRONE_CONFIG.value:
                    result = self._handle_command_get_droneconfig(data)
                    self.databaseRequests.send('{0} {1}'.format(Messages.OK.value, json.dumps(result)))
                elif cmd == Messages.DRONE_CONFIG_CHANGED.value:
                    # TODO: this should be removed when all db activity are contained within this actor
                    # send OK straight away - we don't want the sender to wait
                    self.databaseRequests.send('{0} {1}'.format(Messages.OK.value, '{}'))
                    self._handle_command_drone_config_changed(data)
                elif cmd == Messages.BAIT_USER_ADD.value:
                    self._handle_command_bait_user_add(data)
                    self.databaseRequests.send('{0} {1}'.format(Messages.OK.value, '{}'))
                elif cmd == Messages.BAIT_USER_DELETE.value:
                    self._handle_command_bait_user_delete(data)
                    self.databaseRequests.send('{0} {1}'.format(Messages.OK.value, '{}'))
                elif cmd == Messages.DRONE_DELETE.value:
                    self._handle_command_delete_drone(data)
                    self.databaseRequests.send('{0} {1}'.format(Messages.OK.value, '{}'))
                elif cmd == Messages.DRONE_ADD.value:
                    print 'add'
                    self._handle_command_add_drone()
                else:
                    logger.error('Unknown message received: {0}'.format(data))
                    assert False

    def _start_recurring_classify_set(self):
        while True:
            sleep_time = self.delay_seconds / 2
            gevent.sleep(sleep_time)
            self.do_classify = True

    def persist_session(self, session_json, session_type):
        db_session = database_setup.get_session()

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

        classification = db_session.query(Classification).filter(Classification.type == 'pending').one()

        assert data['honeypot_id'] is not None
        _honeypot = db_session.query(Honeypot).filter(Honeypot.id == data['honeypot_id']).one()
        if session_type == Messages.SESSION_HONEYPOT.value:
            session = Session()
            for entry in data['transcript']:
                transcript_timestamp = datetime.strptime(entry['timestamp'], '%Y-%m-%dT%H:%M:%S.%f')
                transcript = Transcript(timestamp=transcript_timestamp, direction=entry['direction'],
                                        data=entry['data'])
                session.transcript.append(transcript)

            for auth in data['login_attempts']:
                authentication = self.extract_auth_entity(auth)
                session.authentication.append(authentication)
        elif session_type == Messages.SESSION_CLIENT.value:
            ignore_failed_bait_sessions = self.send_config_request('{0} {1}'.format(Messages.GET_CONFIG_ITEM.value,
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
        if session_type == Messages.SESSION_HONEYPOT.value:
            if matching_session:
                self.merge_bait_and_session(session, matching_session, db_session)
        elif session_type == Messages.SESSION_CLIENT.value:
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
        logger.debug('Session dist: {0}'.format(session.discriminator))
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
            if potential_match.discriminator == session.discriminator:
                continue
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
        self.processedSessionsPublisher.send(
            '{0} {1} {2}'.format(Messages.DELETED_DUE_TO_MERGE.value, honeypot_session.id,
                                 bait_session.id))
        self.processedSessionsPublisher.send('{0} {1}'.format(Messages.SESSION.value,
                                                              json.dumps(bait_session.to_dict())))

    def classify_malicious_sessions(self):
        """
        Will classify all unclassified sessions as malicious activity.

        :param delay_seconds: no sessions newer than (now - delay_seconds) will be processed.
        """
        min_datetime = datetime.utcnow() - timedelta(seconds=self.delay_seconds)

        db_session = database_setup.get_session()

        # find and process bait sessions that did not get classified during persistence.
        bait_sessions = db_session.query(BaitSession).options(joinedload(BaitSession.authentication)) \
            .filter(BaitSession.classification_id == 'pending') \
            .filter(BaitSession.did_complete == True) \
            .filter(BaitSession.received < min_datetime).all()

        for bait_session in bait_sessions:
            logger.debug('Classifying bait session with id {0} as MITM'.format(bait_session.id))
            bait_session.classification = db_session.query(Classification).filter(Classification.type == 'mitm').one()
            db_session.commit()

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
            self.processedSessionsPublisher.send(
                '{0} {1}'.format(Messages.SESSION.value, json.dumps(session.to_dict())))

    def _handle_command_delete_drone(self, data):
        drone_id = data
        logger.debug('Deleting drone: {0}'.format(drone_id))
        db_session = database_setup.get_session()
        drone_to_delete = db_session.query(Drone).filter(Drone.id == drone_id).first()
        if drone_to_delete:
            db_session.delete(drone_to_delete)
            db_session.commit()
            # tell the drone to kill itself
            self.drone_command_receiver.send('{0} {1} '.format(drone_id, Messages.DRONE_DELETE.value))
            self._remove_zmq_keys(drone_id)
            self._reconfigure_all_clients()

    def _handle_command_add_drone(self):
        db_session = database_setup.get_session()
        drone = Drone()
        db_session.add(drone)
        db_session.commit()
        logger.debug('New drone has been added with id: {0}'.format(drone.id))

        drone_config = self._get_drone_config(drone.id)
        self.databaseRequests.send('{0} {1}'.format(Messages.OK.value, json.dumps(drone_config)))

    def _reconfigure_all_clients(self):
        db_session = database_setup.get_session()
        db_session.query(DroneEdge).delete()
        db_session.commit()
        honeypots = db_session.query(Honeypot).all()
        clients = db_session.query(Client).all()
        # delete old architecture
        credentials = db_session.query(BaitUser).all()
        for honeypot in honeypots:
            for capability in honeypot.capabilities:
                for client in clients:
                    # following three variables should be make somewhat user configurable again
                    client_timings = json.loads(client.bait_timings)
                    if capability.protocol in client_timings:
                        # the time range in which to activate the bait sessions
                        activation_range = client_timings[capability.protocol]['active_range']
                        # period to sleep before using activation_probability
                        sleep_interval = client_timings[capability.protocol]['sleep_interval']
                        # the probability that a bait session will be activated, 1 is always activate
                        activation_probability = client_timings[capability.protocol]['activation_probability']
                    else:
                        logger.warning('Bait timings for {0} not found on client drone {1}({2}), using defaults instead'
                                       .format(capability.protocol, client.name, client.id))
                        activation_range = '00:00 - 23:59'
                        sleep_interval = '60'
                        activation_probability = 1
                    bait_credentials = random.choice(credentials)
                    client.add_bait(capability, activation_range, sleep_interval,
                                    activation_probability, bait_credentials.username, bait_credentials.password)
        db_session.commit()

        drones = db_session.query(Drone).all()
        for drone in drones:
            self._send_config_to_drone(drone.id)

    def _handle_command_get_droneconfig(self, drone_id):
        return self._get_drone_config(drone_id)

    def _send_config_to_drone(self, drone_id):
        config = self._get_drone_config(drone_id)
        logger.debug('Sending config to {0}: {1}'.format(drone_id, config))
        self.drone_command_receiver.send('{0} {1} {2}'.format(drone_id, Messages.CONFIG.value, json.dumps(config)))

    def send_config_request(self, request):
        return send_zmq_request_socket(self.config_actor_socket, request)

    def _handle_command_drone_config_changed(self, drone_id):
        self._send_config_to_drone(drone_id)
        self._reconfigure_all_clients()

    def _handle_command_bait_user_delete(self, data):
        bait_user_id = int(data)
        db_session = database_setup.get_session()
        bait_user = db_session.query(BaitUser).filter(BaitUser.id == bait_user_id).first()
        if bait_user:
            db_session.delete(bait_user)
            db_session.commit()
            self._bait_user_changed(bait_user.username, bait_user.password)
        else:
            logger.warning('Tried to delete non-existing bait user with id {0}.'.format(bait_user_id))

    def _handle_command_bait_user_add(self, data):
        username, password = data.split(' ')
        db_session = database_setup.get_session()
        existing_bait_user = db_session.query(BaitUser).filter(BaitUser.username == username,
                                                               BaitUser.password == password).first()
        if not existing_bait_user:
            new_bait_user = BaitUser(username=username, password=password)
            db_session.add(new_bait_user)
            db_session.commit()

    def _bait_user_changed(self, username, password):
        db_session = database_setup.get_session()
        drone_edge = db_session.query(DroneEdge).filter(DroneEdge.username == username,
                                                        DroneEdge.password == password).first()
        # A drone is using the bait users, reconfigure all
        # TODO: This is lazy, we should only reconfigure the drone(s) who are actually
        # using the credentials
        if drone_edge:
            self._reconfigure_all_clients()

    def _get_drone_config(self, drone_id):
        db_session = database_setup.get_session()
        drone = db_session.query(Honeypot).filter(Drone.id == drone_id).first()
        # lame! what is the correct way?
        if not drone:
            drone = db_session.query(Client).filter(Drone.id == drone_id).first()
        if not drone:
            drone = db_session.query(Drone).filter(Drone.id == drone_id).first()
        if not drone:
            self.databaseRequests.send(Messages.FAIL.value)

        host = self.send_config_request('{0} {1}'.format(Messages.GET_CONFIG_ITEM.value, 'network,server_host'))
        zmq_port = self.send_config_request('{0} {1}'.format(Messages.GET_CONFIG_ITEM.value, 'network,zmq_port'))
        zmq_command_port = self.send_config_request(
            '{0} {1}'.format(Messages.GET_CONFIG_ITEM.value, 'network,zmq_command_port'))

        server_zmq_url = 'tcp://{0}:{1}'.format(host, zmq_port)
        server_zmq_command_url = 'tcp://{0}:{1}'.format(host, zmq_command_port)

        zmq_keys = self.send_config_request('{0} {1}'.format(Messages.GET_ZMQ_KEYS.value, drone_id))
        zmq_server_key = self.send_config_request('{0} {1}'.format(Messages.GET_ZMQ_KEYS.value,
                                                                   'network,zmq_server_public_key'))
        zmq_server_key = zmq_server_key['public_key']
        # common section that goes for all types of drones
        drone_config = {
            'general': {
                'mode': drone.discriminator,
                'id': int(drone.id),
                'fetch_ip': False,
                'name': drone.name
            },
            'beeswarm_server': {
                'zmq_url': server_zmq_url,
                'zmq_command_url': server_zmq_command_url,
                'zmq_server_public': zmq_server_key,
                'zmq_own_public': zmq_keys['public_key'],
                'zmq_own_private': zmq_keys['private_key'],
            },
            'timecheck': {
                'enabled': True,
                'poll': 5,
                'ntp_pool': 'pool.ntp.org'
            }
        }

        if drone.discriminator == 'honeypot':
            drone_config['certificate_info'] = {
                'common_name': drone.cert_common_name,
                'country': drone.cert_country,
                'state': drone.cert_state,
                'locality': drone.cert_locality,
                'organization': drone.cert_organization,
                'organization_unit': drone.cert_organization_unit
            }
            drone_config['capabilities'] = {}
            for capability in drone.capabilities:
                users = {}
                for bait in capability.baits:
                    users[bait.username] = bait.password
                drone_config['capabilities'][capability.protocol] = {'port': capability.port,
                                                                     'enabled': True,
                                                                     'protocol_specific_data': json.loads(
                                                                         capability.protocol_specific_data),
                                                                     'users': users}
        elif drone.discriminator == 'client':
            drone_config['baits'] = {}
            for bait in drone.baits:
                _bait = {'server': bait.capability.honeypot.ip_address,
                         'port': bait.capability.port,
                         'honeypot_id': bait.capability.honeypot_id,
                         'username': bait.username,
                         'password': bait.password,
                         'active_range': bait.activation_range,
                         'sleep_interval': bait.sleep_interval,
                         'activation_probability': bait.activation_probability}
                if bait.capability.honeypot_id not in drone_config['baits']:
                    drone_config['baits'][bait.capability.honeypot_id] = {}
                assert bait.capability.protocol not in drone_config['baits'][bait.capability.honeypot_id]
                drone_config['baits'][bait.capability.honeypot_id][bait.capability.protocol] = _bait
            if drone.bait_timings:
                drone_config['bait_timings'] = json.loads(drone.bait_timings)
            else:
                drone_config['bait_timings'] = {}

        return drone_config
