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
import os
import sys
import shutil
import _socket
import json

import ntplib
import gevent
from gevent import Greenlet
from gevent.server import StreamServer
import requests
from requests.exceptions import Timeout, ConnectionError

import beeswarm
from beeswarm.drones.honeypot.capabilities import handlerbase
from beeswarm.drones.honeypot.models.session import Session
from beeswarm.drones.honeypot.consumer.consumer import Consumer
from beeswarm.shared.helpers import create_self_signed_cert, send_zmq_push, extract_keys, get_most_likely_ip
from beeswarm.shared.asciify import asciify
from beeswarm.shared.message_enum import Messages


logger = logging.getLogger(__name__)


class Honeypot(object):
    """ This is the main class, which starts up all the capabilities. """

    def __init__(self, work_dir, config, key='server.key', cert='server.crt', **kwargs):
        """
            Main class which runs Beeswarm in Honeypot mode.

        :param work_dir: Working directory (usually the current working directory)
        :param config: Beeswarm configuration dictionary, None if no configuration was supplied.
        :param key: Key file used for SSL enabled capabilities
        :param cert: Cert file used for SSL enabled capabilities
        """
        if config is None or not os.path.isdir(os.path.join(work_dir, 'data')):
            Honeypot.prepare_environment(work_dir)
            with open('beeswarmcfg.json', 'r') as config_file:
                config = json.load(config_file, object_hook=asciify)
        self.work_dir = work_dir
        self.config = config
        self.key = key
        self.cert = cert

        # TODO: pass honeypot otherwise
        Session.honeypot_id = self.config['general']['id']
        self.id = self.config['general']['id']

        # write ZMQ keys to files - as expected by pyzmq
        extract_keys(work_dir, config)
        if not (os.path.isfile(os.path.join(work_dir, 'server.key'))):
            cert_info = config['certificate_info']
            if cert_info['common_name']:
                cert_info['common_name'] = cert_info['common_name']
            else:
                cert_info['common_name'] = get_most_likely_ip()

            cert, priv_key = create_self_signed_cert(cert_info['country'], cert_info['state'],
                                                     cert_info['organization'], cert_info['locality'],
                                                     cert_info['organization_unit'], cert_info['common_name'])

            cert_path = os.path.join(work_dir, 'server.crt')
            key_path = os.path.join(work_dir, 'server.key')
            with open(cert_path, 'w') as certfile:
                certfile.write(cert)
            with open(key_path, 'w') as keyfile:
                keyfile.write(priv_key)
            send_zmq_push('ipc://serverRelay', '{0} {1} {2}'.format(Messages.KEY, self.id, keyfile))
            send_zmq_push('ipc://serverRelay', '{0} {1} {2}'.format(Messages.CERT, self.id, cert))

        if self.config['general']['fetch_ip']:
            try:
                url = 'http://api.externalip.net/ip'
                req = requests.get(url)
                self.honeypot_ip = req.text
                logger.info('Fetched {0} as external ip for Honeypot.'.format(self.honeypot_ip))
            except (Timeout, ConnectionError) as e:
                logger.warning('Could not fetch public ip: {0}'.format(e))
        else:
            self.honeypot_ip = ''

        # spawning time checker
        if self.config['timecheck']['enabled']:
            Greenlet.spawn(self.checktime)

    # function to check the time offset
    def checktime(self):
        """ Make sure our Honeypot time is consistent, and not too far off
        from the actual time. """

        poll = self.config['timecheck']['poll']
        ntp_poll = self.config['timecheck']['ntp_pool']
        while True:
            clnt = ntplib.NTPClient()
            response = clnt.request(ntp_poll, version=3)
            diff = response.offset
            if abs(diff) >= 5:
                logger.error('Timings found to be far off. ({0})'.format(diff))
                sys.exit(1)
            gevent.sleep(poll * 60 * 60)

    def start(self):
        """ Starts services. """
        self.servers = []
        self.server_greenlets = []
        # will contain Session objects
        self.sessions = {}

        # greenlet to consume the provided sessions
        self.session_consumer = Consumer(self.sessions, self.honeypot_ip, self.config)
        Greenlet.spawn(self.session_consumer.start)

        # protocol handlers
        for c in handlerbase.HandlerBase.__subclasses__():

            cap_name = c.__name__.lower()

            if cap_name in self.config['capabilities']:
                port = self.config['capabilities'][cap_name]['port']
                # carve out the options for this specific service
                options = self.config['capabilities'][cap_name]
                cap = c(self.sessions, options, self.work_dir)

                try:
                    # Convention: All capability names which end in 's' will be wrapped in ssl.
                    if cap_name.endswith('s'):
                        server = StreamServer(('0.0.0.0', port), cap.handle_session,
                                              keyfile=self.key, certfile=self.cert)
                    else:
                        server = StreamServer(('0.0.0.0', port), cap.handle_session)

                    logger.debug('Adding {0} capability with options: {1}'.format(cap_name, options))
                    self.servers.append(server)
                    server_greenlet = Greenlet(server.start())
                    self.server_greenlets.append(server_greenlet)

                except _socket.error as ex:
                    logger.error("Could not start {0} server on port {1}. Error: {2}".format(c.__name__, port, ex))
                else:
                    logger.info('Started {0} capability listening on port {1}'.format(c.__name__, port))

        logger.info("Honeypot running.")

        gevent.joinall(self.server_greenlets)

    def stop(self):
        """Stops services"""
        for s in self.servers:
            s.stop()

        for g in self.server_greenlets:
            g.kill()

        self.session_consumer.stop()
        logger.info('All workers stopped.')

    @staticmethod
    def prepare_environment(work_dir):
        """
            Performs a few maintenance tasks before the Honeypot is run. Copies the data directory,
            and the config file to the cwd. The config file copied here is overwritten if
            the __init__ method is called with a configuration URL.

        :param work_dir: The directory to copy files to.
        """
        package_directory = os.path.dirname(os.path.abspath(beeswarm.__file__))

        logger.info('Copying data files to workdir.')
        shutil.copytree(os.path.join(package_directory, 'drones/honeypot/data'), os.path.join(work_dir, 'data/'),
                        ignore=Honeypot._ignore_copy_files)

        # this config file is for standalone operations, it will be overwritten during __init__
        # if a config url is specified.
        config_file = os.path.join(work_dir, 'beeswarmcfg.json.dist')
        if not os.path.isfile('beeswarmcfg.json'):
            logger.info('Copying configuration file to workdir.')
            shutil.copyfile(os.path.join(package_directory, 'drones/honeypot/beeswarmcfg.json.dist'),
                            os.path.join(work_dir, 'beeswarmcfg.json'))

    @staticmethod
    def _ignore_copy_files(path, content):
        to_ignore = []
        for file_ in content:
            if file_ in ('.placeholder', '.git'):
                to_ignore.append(file_)
        return to_ignore
