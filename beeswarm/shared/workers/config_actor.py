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
from zmq.auth.certs import create_certificates, load_certificate
import beeswarm
from beeswarm.shared.message_enum import Messages

logger = logging.getLogger(__name__)


class ConfigActor(Greenlet):
    def __init__(self, config_file, work_dir):
        Greenlet.__init__(self)
        self.config_file = os.path.join(work_dir, config_file)
        self.config = json.load(open(self.config_file, 'r'))
        self.work_dir = work_dir

        context = zmq.Context()
        self.config_publisher = context.socket(zmq.PUB)
        self.config_commands = context.socket(zmq.REP)
        self.enabled = True

    def close(self):
        self.config_publisher.close()
        self.config_commands.close()
        self.enabled = False

    def _run(self):
        # start accepting incomming messages
        self.config_commands.bind('ipc://configCommands')
        self.config_publisher.bind('ipc://configPublisher')
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

        if cmd == Messages.SET:
            self._handle_command_set(data)
        elif cmd == Messages.GEN_ZMQ_KEYS:
            self._handle_command_genkeys(data)
        elif cmd == Messages.PUBLISH_CONFIG:
            self._publish_config()
            self.config_commands.send('{0} {1}'.format(Messages.OK, '{}'))
        else:
            self.config_commands.send(Messages.FAIL)

    def _handle_command_set(self, data):
        new_config = json.loads(data)
        # all keys must in the original dict
        if all(key in self.config for key in new_config):
            self.config_commands.send('{0} {1}'.format(Messages.OK, '{}'))
            self.config.update(new_config)
            self._save_config_file()
            self._publish_config()
        else:
            self.config_commands.send(Messages.FAIL)

    def _handle_command_genkeys(self, name):
        private_key, publickey = self._generate_zmq_keys(name)
        self.config_commands.send(Messages.OK + ' ' + json.dumps({'public_key': publickey,
                                                                  'private_key': private_key}))

    def _publish_config(self):
        logger.debug('Sending config to subscribers.')
        self.config_publisher.send('{0} {1}'.format(Messages.CONFIG_FULL, json.dumps(self.config)))

    def _save_config_file(self):
        with open(self.config_file, 'r+') as config_file:
            config_file.write(json.dumps(self.config, indent=4))

    def _generate_zmq_keys(self, key_name):
        cert_path = os.path.join(self.work_dir, 'certificates')
        public_keys = os.path.join(cert_path, 'public_keys')
        private_keys = os.path.join(cert_path, 'private_keys')
        for _path in [cert_path, public_keys, private_keys]:
            if not os.path.isdir(_path):
                os.mkdir(_path)

        tmp_key_dir = tempfile.mkdtemp()
        try:
            public_key, private_key = create_certificates(tmp_key_dir, key_name)
            # the final location for keys
            public_key_final = os.path.join(public_keys, '{0}.pub'.format(key_name))
            private_key_final = os.path.join(private_keys, '{0}.pri'.format(key_name))
            shutil.move(public_key, public_key_final)
            shutil.move(private_key, private_key_final)
        finally:
            shutil.rmtree(tmp_key_dir)

        # return copy of keys
        return open(private_key_final, "r").readlines(), open(public_key_final, "r").readlines()
