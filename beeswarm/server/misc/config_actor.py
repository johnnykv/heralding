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
import os
import tempfile
import shutil
import random

from gevent import Greenlet
import zmq.green as zmq
from zmq.auth.certs import create_certificates
from beeswarm.shared.message_enum import Messages
from beeswarm.server.db import database_setup
from beeswarm.server.db.entities import Client, Honeypot, Drone, DroneEdge, BaitUser

logger = logging.getLogger(__name__)


class ConfigActor(Greenlet):
    def __init__(self, config_file, work_dir):
        Greenlet.__init__(self)
        self.config_file = os.path.join(work_dir, config_file)
        if not os.path.exists(self.config_file):
            self.config = {}
            self._save_config_file()
        self.config = json.load(open(self.config_file, 'r'))
        self.work_dir = work_dir

        context = zmq.Context()
        self.config_publisher = context.socket(zmq.PUB)
        self.config_commands = context.socket(zmq.REP)
        self.drone_command_receiver = context.socket(zmq.PUSH)
        self.enabled = True

    def close(self):
        self.config_publisher.close()
        self.config_commands.close()
        self.enabled = False

    def _run(self):
        # start accepting incomming messages
        self.config_commands.bind('ipc://configCommands')
        self.config_publisher.bind('ipc://configPublisher')
        self.drone_command_receiver.connect('ipc://droneCommandReceiver')

        # initial publish of config
        self._publish_config()

        poller = zmq.Poller()
        poller.register(self.config_commands, zmq.POLLIN)
        poller.register(self.config_publisher, zmq.POLLIN)
        while self.enabled:
            socks = dict(poller.poll(500))
            if self.config_commands in socks and socks[self.config_commands] == zmq.POLLIN:
                self._handle_commands()

    def _handle_commands(self):
        msg = self.config_commands.recv()

        if ' ' in msg:
            cmd, data = msg.split(' ', 1)
        else:
            cmd = msg
        logger.debug('Received command: {0}'.format(cmd))

        if cmd == Messages.SET:
            self._handle_command_set(data)
        elif cmd == Messages.GEN_ZMQ_KEYS:
            self._handle_command_genkeys(data)
        elif cmd == Messages.PUBLISH_CONFIG:
            self._publish_config()
            self.config_commands.send('{0} {1}'.format(Messages.OK, '{}'))
        elif cmd == Messages.DRONE_CONFIG:
            result = self._handle_command_get_droneconfig(data)
            self.config_commands.send('{0} {1}'.format(Messages.OK, json.dumps(result)))
        elif cmd == Messages.DRONE_CONFIG_CHANGED:
            # send OK straight away - we don't want the sender to wait
            self.config_commands.send('{0} {1}'.format(Messages.OK, '{}'))
            self._handle_command_drone_config_changed(data)
        else:
            logger.warning('Unknown command received: {0}'.format(cmd))
            self.config_commands.send(Messages.FAIL)

    def _handle_command_set(self, data):
        new_config = json.loads(data)
        self.config_commands.send('{0} {1}'.format(Messages.OK, '{}'))
        self.config.update(new_config)
        self._save_config_file()
        self._publish_config()

    def _handle_command_genkeys(self, name):
        private_key, publickey = self._get_zmq_keys(name)
        self.config_commands.send(Messages.OK + ' ' + json.dumps({'public_key': publickey,
                                                                  'private_key': private_key}))

    def _handle_command_drone_config_changed(self, drone_id):
        config_json = self._get_drone_config(drone_id)
        self.drone_command_receiver.send('{0} {1} {2}'.format(drone_id, Messages.CONFIG, json.dumps(config_json)))
        self._reconfigure_all_clients()

    def _handle_command_get_droneconfig(self, id):
        return self._get_drone_config(id)

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

                    # the range in which to activate bait sessions
                    activation_range = '00:00 - 23:59'
                    # period to sleep before using activation_probability
                    sleep_interval = '60'
                    # the probability that a bait session will be activated, 1 is always activate
                    activation_probability = 1
                    bait_credentials = random.choice(credentials)
                    client.add_bait(capability, activation_range, sleep_interval,
                                    activation_probability, bait_credentials.username, bait_credentials.password)
        db_session.commit()
        for client in clients:
            self._handle_command_drone_config_changed(client.id)

    def _get_drone_config(self, id):
        db_session = database_setup.get_session()
        drone = db_session.query(Honeypot).filter(Drone.id == id).first()
        # lame! what is the correct way?
        if not drone:
            drone = db_session.query(Client).filter(Drone.id == id).first()
        if not drone:
            drone = db_session.query(Drone).filter(Drone.id == id).first()
        if not drone:
            self.config_commands.send(Messages.FAIL)

        server_zmq_url = 'tcp://{0}:{1}'.format(self.config['network']['server_host'], self.config['network']['zmq_port'])
        server_zmq_command_url = 'tcp://{0}:{1}'.format(self.config['network']['server_host'],
                                                        self.config['network']['zmq_command_port'])

        private_key, public_key = self._get_zmq_keys(str(drone.id))

        # common section that goes for all types of drones
        drone_config = {
            'general': {
                'mode': drone.discriminator,
                'id': id,
                'fetch_ip': False,
                'name': drone.name
            },
            'beeswarm_server': {
                'zmq_url': server_zmq_url,
                'zmq_command_url': server_zmq_command_url,
                'zmq_server_public': self.config['network']['zmq_server_public_key'],
                'zmq_own_public': public_key,
                'zmq_own_private': private_key,
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
            drone_config['users'] = {}
            drone_config['capabilities'] = {}
            for capability in drone.capabilities:
                drone_config['capabilities'][capability.protocol] = {'port': capability.port,
                                                                     'enabled': True,
                                                                     'protocol_specific_data': capability.protocol_specific_data}
        elif drone.discriminator == 'client':
            drone_config['baits'] = {}
            for bait in drone.baits:
                drone_config['baits'][bait.capability.protocol] = {'server': bait.capability.honeypot.id,
                                                                   'port': bait.capability.port,
                                                                   'username': bait.username,
                                                                   'password': bait.password}

        return drone_config

    def _publish_config(self):
        logger.debug('Sending config to subscribers.')
        self.config_publisher.send('{0} {1}'.format(Messages.CONFIG_FULL, json.dumps(self.config)))

    def _save_config_file(self):
        with open(self.config_file, 'w+') as config_file:
            config_file.write(json.dumps(self.config, indent=4))

    def _get_zmq_keys(self, id):
        cert_path = os.path.join(self.work_dir, 'certificates')
        public_keys = os.path.join(cert_path, 'public_keys')
        private_keys = os.path.join(cert_path, 'private_keys')
        public_key_path = os.path.join(public_keys, '{0}.pub'.format(id))
        private_key_path = os.path.join(private_keys, '{0}.pri'.format(id))

        if not os.path.isfile(public_key_path) or not os.path.isfile(private_key_path):
            logging.debug('Generating ZMQ keys for: {0}.'.format(id))
            for _path in [cert_path, public_keys, private_keys]:
                if not os.path.isdir(_path):
                    os.mkdir(_path)

            tmp_key_dir = tempfile.mkdtemp()
            try:
                public_key, private_key = create_certificates(tmp_key_dir, id)
                # the final location for keys
                shutil.move(public_key, public_key_path)
                shutil.move(private_key, private_key_path)
            finally:
                shutil.rmtree(tmp_key_dir)

        # return copy of keys
        return open(private_key_path, "r").readlines(), open(public_key_path, "r").readlines()
