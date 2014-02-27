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

import gevent.event
import zmq.green as zmq

logger = logging.getLogger(__name__)


class ConfigActor(object):
    def __init__(self, config_file):
        self.config_file = config_file
        self.config = json.load(open(self.config_file, 'r'))

        context = zmq.Context()
        self.config_publisher = context.socket(zmq.XPUB)
        self.config_setter = context.socket(zmq.REP)
        gevent.spawn(self._start)

    def _start(self):
        # start accepting incomming messages
        self.config_setter.bind('ipc://configSetter')
        self.config_publisher.bind('ipc://configPublisher')
        # initial publish of config
        self._publish_config()

        poller = zmq.Poller()
        poller.register(self.config_setter, zmq.POLLIN)
        poller.register(self.config_publisher, zmq.POLLIN)
        while True:
            socks = dict(poller.poll())
            if self.config_setter in socks and socks[self.config_setter] == zmq.POLLIN:
                self._handle_setters()
            if self.config_publisher in socks and socks[self.config_publisher] == zmq.POLLIN:
                self._handle_subscriptions()

    def _handle_subscriptions(self):
        raw_msg = self.config_publisher.recv(zmq.NOBLOCK)
        # publish config if we have a new subscriber
        if raw_msg[0] == "\x01":
            logger.debug('SUBSCRIBE')
            self._publish_config()

    def _handle_setters(self):
        raw_msg = self.config_setter.recv()
        new_config = json.loads(raw_msg)
        # all keys must in the original dict
        if all(key in self.config for key in new_config):
            self.config_setter.send('ok')
            self.config.update(new_config)
            self._save_config_file()
            self._publish_config()
        else:
            self.config_setter.send('fail')

    def _publish_config(self):
        self.config_publisher.send('{0} {1}'.format('full', json.dumps(self.config)))

    def _save_config_file(self):
        with open(self.config_file, 'r+') as config_file:
            config_file.write(json.dumps(self.config, indent=4))