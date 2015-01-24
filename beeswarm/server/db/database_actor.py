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
from sqlalchemy import desc

import beeswarm
import beeswarm.shared
from beeswarm.server.db import database_setup
from beeswarm.server.db.entities import BaitSession, Session, Client, Authentication, Classification, \
    Transcript, Honeypot, Drone, DroneEdge, BaitUser
from beeswarm.shared.helpers import send_zmq_request_socket, generate_cert_digest
from beeswarm.shared.message_enum import Messages
from beeswarm.shared.socket_enum import SocketNames


logger = logging.getLogger(__name__)


class DatabaseActor(gevent.Greenlet):
    def __init__(self, max_sessions, clear_sessions=False, delay_seconds=30):
        assert delay_seconds > 1
        Greenlet.__init__(self)
        db_session = database_setup.get_session()
        self.enabled = True
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
        self.do_maintenance = False
        if clear_sessions or max_sessions == 0:
            db_session = database_setup.get_session()
            count = db_session.query(Session).delete()
            logging.info('Deleting {0} sessions on startup.'.format(count))
            db_session.commit()

        self.max_session_count = max_sessions
        if max_sessions:
            logger.info('Database has been limited to contain {0} sessions.'.format(max_sessions))

        context = beeswarm.shared.zmq_context

        # prepare sockets
        self.drone_data_socket = context.socket(zmq.SUB)
        self.processedSessionsPublisher = context.socket(zmq.PUB)
        self.databaseRequests = context.socket(zmq.REP)
        self.config_actor_socket = context.socket(zmq.REQ)
        self.drone_command_receiver = context.socket(zmq.PUSH)

    def _run(self):
        # connect and bind to all relevant sockets
        # raw data from drones
        self.drone_data_socket.connect(SocketNames.DRONE_DATA.value)
        self.drone_data_socket.setsockopt(zmq.SUBSCRIBE, '')
        # requests that this actor needs to respond to
        self.databaseRequests.bind(SocketNames.DATABASE_REQUESTS.value)
        # will publish session after they have been processed on this socket
        self.processedSessionsPublisher.bind(SocketNames.PROCESSED_SESSIONS.value)
        # needed to be able to probe for options and get zmq keys
        self.config_actor_socket.connect(SocketNames.CONFIG_COMMANDS.value)
        # needed to send data directly to drones
        self.drone_command_receiver.connect(SocketNames.DRONE_COMMANDS.value)

        poller = zmq.Poller()
        poller.register(self.drone_data_socket, zmq.POLLIN)
        poller.register(self.databaseRequests, zmq.POLLIN)
        gevent.spawn(self._start_recurring_classify_set)
        gevent.spawn(self._start_recurring_maintenance_set)
        while self.enabled:
            socks = dict(poller.poll(100))
            if self.do_classify:
                self._classify_malicious_sessions()
                self.do_classify = False
            elif self.do_maintenance:
                self._db_maintenance()
                self.do_maintenance = False
            elif self.databaseRequests in socks and socks[self.databaseRequests] == zmq.POLLIN:
                data = self.databaseRequests.recv()
                if ' ' in data:
                    cmd, data = data.split(' ', 1)
                else:
                    cmd = data

                if cmd == Messages.DRONE_CONFIG.value:
                    self._handle_command_get_droneconfig(data)
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
                    self._handle_command_add_drone()
                elif cmd == Messages.GET_DB_STATS.value:
                    result = self._handle_command_get_db_stats()
                    self.databaseRequests.send('{0} {1}'.format(Messages.OK.value, json.dumps(result)))
                elif cmd == Messages.GET_SESSIONS_ALL.value or cmd == Messages.GET_SESSIONS_ATTACKS.value \
                        or cmd == Messages.GET_SESSIONS_BAIT.value:
                    # TODO: Accept to/from param to facilitate pagination
                    result = self._handle_command_get_sessions(cmd)
                    self.databaseRequests.send('{0} {1}'.format(Messages.OK.value, json.dumps(result)))
                elif cmd == Messages.GET_SESSION_CREDENTIALS.value:
                    result = self._handle_command_get_credentials(data)
                    self.databaseRequests.send('{0} {1}'.format(Messages.OK.value, json.dumps(result)))
                elif cmd == Messages.GET_SESSION_TRANSCRIPT.value:
                    result = self._handle_command_get_transcript(data)
                    self.databaseRequests.send('{0} {1}'.format(Messages.OK.value, json.dumps(result)))
                elif cmd == Messages.GET_BAIT_USERS.value:
                    result = self._handle_command_get_bait_users()
                    self.databaseRequests.send('{0} {1}'.format(Messages.OK.value, json.dumps(result)))
                elif cmd == Messages.CONFIG_DRONE.value:
                    # .send on socket is handled internally since it can send errors back
                    self._handle_command_config_drone(data)
                elif cmd == Messages.GET_DRONE_LIST.value:
                    result = self._handle_command_get_drone_list(data)
                    self.databaseRequests.send('{0} {1}'.format(Messages.OK.value, json.dumps(result)))
                else:
                    logger.error('Unknown message received: {0}'.format(data))
                    assert False
            elif self.drone_data_socket in socks and socks[self.drone_data_socket] == zmq.POLLIN:
                split_data = self.drone_data_socket.recv().split(' ', 2)
                if len(split_data) == 3:
                    topic, drone_id, data = split_data
                else:
                    data = None
                    topic, drone_id, = split_data
                self._update_drone_last_activity(drone_id)
                if topic == Messages.SESSION_HONEYPOT.value or topic == Messages.SESSION_CLIENT.value:
                    self.persist_session(topic, data)
                elif topic == Messages.CERT.value:
                    self._handle_cert_message(topic, drone_id, data)
                elif topic == Messages.KEY.value:
                    pass
                elif topic == Messages.IP.value:
                    self._handle_message_ip(topic, drone_id, data)
                elif topic == Messages.DRONE_WANT_CONFIG.value:
                    config_dict = self._get_drone_config(drone_id)
                    self.drone_command_receiver.send('{0} {1} {2}'.format(drone_id, Messages.CONFIG.value,
                                                                          json.dumps(config_dict)))
                elif topic == Messages.PING.value:
                    logger.debug('Received ping from {0}'.format(drone_id))
                else:
                    logger.debug('This actor cannot process this message: {0}'.format(topic))

    def stop(self):
        self.enabled = False
        self.drone_data_socket.close()
        self.processedSessionsPublisher.close()
        self.databaseRequests.close()
        self.config_actor_socket.close()
        self.drone_command_receiver.close()

    def _update_drone_last_activity(self, drone_id):
        db_session = database_setup.get_session()
        drone = db_session.query(Drone).filter(Drone.id == drone_id).one()
        if drone:
            drone.last_activity = datetime.now()
            db_session.add(drone)
            db_session.commit()
        else:
            logger.warning('Trying to update last activity non-exting drone with id {0}'.format(drone_id))

    def _start_recurring_maintenance_set(self):
        while self.enabled:
            sleep_time = 60 * 60
            gevent.sleep(sleep_time)
            self.do_maintenance = True

    def _start_recurring_classify_set(self):
        while self.enabled:
            sleep_time = self.delay_seconds / 2
            gevent.sleep(sleep_time)
            self.do_classify = True

    def _handle_message_ip(self, topic, drone_id, data):
        ip_address = data
        logging.debug('Drone {0} reported ip: {1}'.format(drone_id, ip_address))
        db_session = database_setup.get_session()
        drone = db_session.query(Drone).filter(Drone.id == drone_id).one()
        if drone:
            if drone.ip_address != ip_address:
                drone.ip_address = ip_address
                db_session.add(drone)
                db_session.commit()
        else:
            logger.warning('Trying to update IP on non-exting drone with id {0}'.format(drone_id))

    def _handle_cert_message(self, topic, drone_id, data):
        # for now we just store the fingerprint
        # in the future it might be relevant to store the entire public key and private key
        # for forensic purposes
        cert = data.split(' ', 1)[1]
        digest = generate_cert_digest(cert)
        logging.debug('Storing public key digest: {0} for drone {1}.'.format(digest, drone_id))
        db_session = database_setup.get_session()
        drone = db_session.query(Drone).filter(Drone.id == drone_id).one()
        if drone:
            drone.cert_digest = digest
            db_session.add(drone)
            db_session.commit()
        else:
            logger.warning('Trying to update cert on non-exting drone with id {0}'.format(drone_id))

    def persist_session(self, session_type, session_json):
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

    def _classify_malicious_sessions(self):
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
            self.send_config_request('{0} {1}'.format(Messages.DELETE_ZMQ_KEYS.value, drone_id))
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
        result = self._get_drone_config(drone_id)
        if len(result) == 0:
            self.databaseRequests.send('{0} {1}'.format(Messages.FAIL.value, 'Drone could not be found'))
        else:
            self.databaseRequests.send('{0} {1}'.format(Messages.OK.value, json.dumps(result)))

    def _send_config_to_drone(self, drone_id):
        config = self._get_drone_config(drone_id)
        logger.debug('Sending config to {0}: {1}'.format(drone_id, config))
        self.drone_command_receiver.send('{0} {1} {2}'.format(drone_id, Messages.CONFIG.value, json.dumps(config)))

    def send_config_request(self, request):
        return send_zmq_request_socket(self.config_actor_socket, request)

    def _handle_command_drone_config_changed(self, drone_id):
        self._send_config_to_drone(drone_id)
        # TODO: Only Clients that communicate with this drone_id needs to get reconfigured.
        self._reconfigure_all_clients()

    def _handle_command_bait_user_delete(self, data):
        bait_user_id = int(data)
        db_session = database_setup.get_session()
        bait_user = db_session.query(BaitUser).filter(BaitUser.id == bait_user_id).first()
        if bait_user:
            db_session.delete(bait_user)
            db_session.commit()
            drone_edge = db_session.query(DroneEdge).filter(DroneEdge.username == bait_user.username,
                                                            DroneEdge.password == bait_user.password).first()
            # A drone is using the bait users, reconfigure all
            # TODO: This is lazy, we should only reconfigure the drone(s) who are actually
            # using the credentials
            if drone_edge:
                self._reconfigure_all_clients()
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

    def _handle_command_get_bait_users(self):
        db_session = database_setup.get_session()
        bait_users = db_session.query(BaitUser)
        return_rows = []
        for bait_user in bait_users:
            row = {'id': bait_user.id, 'username': bait_user.username, 'password': bait_user.password}
            return_rows.append(row)
        return return_rows

    def _get_drone_config(self, drone_id):
        db_session = database_setup.get_session()
        drone = db_session.query(Honeypot).filter(Drone.id == drone_id).first()
        # lame! what is the correct way?
        if not drone:
            drone = db_session.query(Client).filter(Drone.id == drone_id).first()
        if not drone:
            drone = db_session.query(Drone).filter(Drone.id == drone_id).first()
        if not drone:
            # drone not found
            return {}

        host = self.send_config_request('{0} {1}'.format(Messages.GET_CONFIG_ITEM.value, 'network,server_host'))
        zmq_port = self.send_config_request('{0} {1}'.format(Messages.GET_CONFIG_ITEM.value, 'network,zmq_port'))
        zmq_command_port = self.send_config_request(
            '{0} {1}'.format(Messages.GET_CONFIG_ITEM.value, 'network,zmq_command_port'))

        server_zmq_url = 'tcp://{0}:{1}'.format(host, zmq_port)
        server_zmq_command_url = 'tcp://{0}:{1}'.format(host, zmq_command_port)

        zmq_keys = self.send_config_request('{0} {1}'.format(Messages.GET_ZMQ_KEYS.value, drone_id))
        zmq_server_key = self.send_config_request('{0} {1}'.format(Messages.GET_ZMQ_KEYS.value, 'beeswarm_server'))
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

    def _handle_command_get_db_stats(self):
        db_session = database_setup.get_session()
        database_stats = {
            'count_honeypots': db_session.query(Honeypot).count(),
            'count_clients': db_session.query(Client).count(),
            'count_sessions': db_session.query(Session).count(),
            'count_all_baits': db_session.query(BaitSession).count(),
            'count_all_attacks': db_session.query(Session).filter(Session.classification_id != 'bait_session')
                .filter(Session.classification_id != 'pending')
                .filter(Session.classification_id is not None).count(),
            'count_attack_type': {
                'http': self._get_num_attacks('http', db_session),
                'vnc': self._get_num_attacks('vnc', db_session),
                'ssh': self._get_num_attacks('ssh', db_session),
                'ftp': self._get_num_attacks('ftp', db_session),
                'https': self._get_num_attacks('https', db_session),
                'pop3': self._get_num_attacks('pop3', db_session),
                'pop3s': self._get_num_attacks('pop3s', db_session),
                'smtp': self._get_num_attacks('smtp', db_session),
                'telnet': self._get_num_attacks('telnet', db_session),
            },
            'baits': {
                'successful': db_session.query(BaitSession).filter(BaitSession.did_login).count(),
                'failed': db_session.query(BaitSession).filter(not BaitSession.did_login).count(),

            }
        }
        return database_stats

    def _get_num_attacks(self, protocol, db_session):
        return db_session.query(Session).filter(Session.classification_id != 'bait_session') \
            .filter(Session.classification_id is not None) \
            .filter(Session.protocol == protocol).count()

    def _handle_command_get_sessions(self, _type):
        db_session = database_setup.get_session()
        # the database_setup will not get hit until we start iterating the query object
        query_iterators = {
            Messages.GET_SESSIONS_ALL.value: db_session.query(Session),
            Messages.GET_SESSIONS_BAIT.value: db_session.query(BaitSession),
            Messages.GET_SESSIONS_ATTACKS.value: db_session.query(Session).filter(
                Session.classification_id != 'bait_session')
        }

        if _type not in query_iterators:
            logger.warning('Query for sessions with unknown type: {0}'.format(_type))
            return []

        # select which iterator to use
        entries = query_iterators[_type].order_by(desc(Session.timestamp))

        rows = []
        for session in entries:
            rows.append(session.to_dict())

        return rows

    def _handle_command_get_credentials(self, session_id):
        db_session = database_setup.get_session()

        credentials = db_session.query(Authentication).filter(Authentication.session_id == session_id)
        return_rows = []
        for credential in credentials:
            return_rows.append(credential.to_dict())
        return return_rows

    def _handle_command_get_transcript(self, session_id):
        db_session = database_setup.get_session()

        transcripts = db_session.query(Transcript).filter(Transcript.session_id == session_id)
        return_rows = []
        for transcript in transcripts:
            row = {'time': transcript.timestamp.strftime('%Y-%m-%d %H:%M:%S'), 'direction': transcript.direction,
                   'data': transcript.data}
            return_rows.append(row)
        return return_rows

    def _handle_command_get_drone_list(self, drone_type):
        db_session = database_setup.get_session()
        if drone_type == 'all':
            drones = db_session.query(Drone).all()
        elif drone_type == 'unassigned':
            drones = db_session.query(Drone).filter(Drone.discriminator == None)
        else:
            drones = db_session.query(Drone).filter(Drone.discriminator == drone_type)

        drone_list = []
        for drone in drones:
            drone_list.append(drone.to_dict())
        return drone_list

    def _handle_command_config_drone(self, data):
        drone_id, config = data.split(' ', 1)
        config = json.loads(config)

        db_session = database_setup.get_session()
        drone = db_session.query(Drone).filter(Drone.id == drone_id).one()
        if not drone:
            self.databaseRequests.send('{0} {1}'.format(Messages.FAIL.value, 'Drone with id {0} could not '
                                                                             'found'.format(drone_id)))
        elif config['mode'] == 'honeypot':
            # it is a honeypot
            self._config_honeypot(drone, db_session, config)
            self.databaseRequests.send('{0} {1}'.format(Messages.OK.value, {}))
        elif config['mode'] == 'client':
            # it is a client
            self._config_client(drone, db_session, config)
            self.databaseRequests.send('{0} {1}'.format(Messages.OK.value, {}))

        else:
            logger.error('Could not detect mode for drone config, drone id: {0}'.format(drone_id))
            self.databaseRequests.send('{0} {1}'.format(Messages.FAIL.value, 'Malformed data in drone config data.'
                                                                             'Drone id: {0}'.format(drone_id)))

    def _config_honeypot(self, drone, db_session, config):
        if drone.discriminator != 'honeypot':
            # meh, better way do do this?
            drone_id = drone.id
            ip_address = drone.ip_address
            db_session.delete(drone)
            db_session.commit()
            drone = Honeypot(id=drone_id)
            drone.ip_address = ip_address
            db_session.add(drone)
            db_session.commit()

        # common properties
        drone.name = config['name']

        # certificate information
        drone.cert_common_name = config['certificate']['common_name']
        drone.cert_country = config['certificate']['country']
        drone.cert_state = config['certificate']['state']
        drone.cert_locality = config['certificate']['locality']
        drone.cert_organization = config['certificate']['organization']
        drone.cert_organization_unit = config['certificate']['organization_unit']

        # add capabilities
        drone.capabilities = []
        for protocol_name, protocol_config in config['capabilities'].items():
            if 'protocol_specific_data' in protocol_config:
                protocol_specific_data = protocol_config['protocol_specific_data']
            else:
                protocol_specific_data = {}
            drone.add_capability(protocol_name, protocol_config['port'], protocol_specific_data)

        db_session.add(drone)
        db_session.commit()
        self._handle_command_drone_config_changed(drone.id)

    def _config_client(self, drone, db_session, config):
        if drone.discriminator != 'client':
            # meh, better way do do this?
            # TODO: this cascade delete sessions, find a way to maintain sessions for deleted drones.
            ip_address = drone.ip_address
            drone_id = drone.id
            db_session.delete(drone)
            db_session.commit()
            drone = Client(id=drone_id)
            drone.ip_address = ip_address
            db_session.add(drone)
            db_session.commit()
        drone.bait_timings = json.dumps(config['bait_timings'])
        drone.name = config['name']
        db_session.add(drone)
        db_session.commit()
        self._handle_command_drone_config_changed(drone.id)

    def _db_maintenance(self):
        logger.debug('Doing database maintenance')
        bait_session_retain_days = int(self.send_config_request('{0} {1}'.format(Messages.GET_CONFIG_ITEM.value,
                                                                                 'bait_session_retain')))
        bait_retain = datetime.utcnow() - timedelta(days=bait_session_retain_days)
        malicious_session_retain_days = int(self.send_config_request('{0} {1}'.format(Messages.GET_CONFIG_ITEM.value,
                                                                                      'malicious_session_retain')))
        malicious_retain = datetime.utcnow() - timedelta(days=malicious_session_retain_days)

        db_session = database_setup.get_session()

        malicious_deleted_count = db_session.query(Session).filter(Session.classification_id != 'bait_session') \
            .filter(Session.timestamp < malicious_retain).delete()

        bait_deleted_count = db_session.query(Session).filter(Session.classification_id == 'bait_session') \
            .filter(Session.timestamp < bait_retain).delete()
        db_session.commit()

        logger.info('Database maintenance finished. Deleted {0} bait_sessions and {1} malicious sessions)'
                    .format(bait_deleted_count, malicious_deleted_count))
