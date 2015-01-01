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

from gevent import Greenlet
import zmq.green as zmq
from zmq.auth.certs import create_certificates

import beeswarm
from beeswarm.shared.message_enum import Messages
from beeswarm.shared.socket_enum import SocketNames


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

        context = beeswarm.shared.zmq_context
        self.config_commands = context.socket(zmq.REP)
        self.enabled = True

    def stop(self):
        self.enabled = False

        if self.config_commands:
            self.config_commands.close()

    def _run(self):
        self.config_commands.bind(SocketNames.CONFIG_COMMANDS.value)

        poller = zmq.Poller()
        poller.register(self.config_commands, zmq.POLLIN)
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

        if cmd == Messages.SET_CONFIG_ITEM.value:
            self._handle_command_set(data)
            self.config_commands.send('{0} {1}'.format(Messages.OK.value, '{}'))
        elif cmd == Messages.GET_CONFIG_ITEM.value:
            value = self._handle_command_get(data)
            self.config_commands.send('{0} {1}'.format(Messages.OK.value, value))
        elif cmd == Messages.GET_ZMQ_KEYS.value:
            self._handle_command_getkeys(data)
        elif cmd == Messages.DELETE_ZMQ_KEYS.value:
            self._remove_zmq_keys(data)
            self.config_commands.send('{0} {1}'.format(Messages.OK.value, '{}'))
        else:
            logger.error('Unknown command received: {0}'.format(cmd))
            self.config_commands.send(Messages.FAIL.value)

    def _handle_command_set(self, data):
        new_config = json.loads(data)
        self.config.update(new_config)
        self._save_config_file()

    def _handle_command_get(self, data):
        # example: 'network,host' will lookup self.config['network']['host']
        keys = data.split(',')
        value = self._retrieve_nested_config(keys, self.config)
        return value

    def _retrieve_nested_config(self, keys, dict):
        if keys[0] in dict:
            if len(keys) == 1:
                return dict[keys[0]]
            else:
                return self._retrieve_nested_config(keys[1:], dict[keys[0]])

    def _handle_command_getkeys(self, name):
        private_key, publickey = self._get_zmq_keys(name)
        self.config_commands.send(Messages.OK.value + ' ' + json.dumps({'public_key': publickey,
                                                                        'private_key': private_key}))

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

    def _remove_zmq_keys(self, id):
        cert_path = os.path.join(self.work_dir, 'certificates')
        public_keys = os.path.join(cert_path, 'public_keys')
        private_keys = os.path.join(cert_path, 'private_keys')
        public_key_path = os.path.join(public_keys, '{0}.pub'.format(id))
        private_key_path = os.path.join(private_keys, '{0}.pri'.format(id))

        for _file in [public_key_path, private_key_path]:
            if os.path.isfile(_file):
                os.remove(_file)



