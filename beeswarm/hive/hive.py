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
import ntplib
import json

import gevent
from gevent import Greenlet
from beeswarm.hive.consumer import consumer

import beeswarm
# Do not remove this import, it is required for auto detect.
# See capabilities/__init__.py to see how the auto detect works
from beeswarm.hive.capabilities import handlerbase

from beeswarm.hive.models.session import Session
from beeswarm.hive.models.authenticator import Authenticator
from beeswarm.hive.helpers.streamserver import HiveStreamServer
from beeswarm.hive.helpers.common import create_socket
from beeswarm.shared.helpers import drop_privileges, create_self_signed_cert, get_local_ipaddress
from beeswarm.hive.models.user import HiveUser
from beeswarm.errors import ConfigNotFound
import requests
from requests.exceptions import Timeout, ConnectionError
from beeswarm.shared.helpers import is_url
from beeswarm.shared.asciify import asciify
from beeswarm.shared.models.ui_handler import UIHandler

logger = logging.getLogger(__name__)


class Hive(object):

    """ This is the main class, which starts up all the capabilities. """

    def __init__(self, work_dir, config_arg='hivecfg.json', key='server.key', cert='server.crt', user_interface=False):
        self.work_dir = work_dir
        self.key = key
        self.cert = cert
        self.show_ui = user_interface

        if not is_url(config_arg):
            if not os.path.exists(config_arg):
                raise ConfigNotFound('Configuration file could not be found. ({0})'.format(config_arg))
            try:
                with open(config_arg, 'r') as cfg:
                    self.config = json.load(cfg, object_hook=asciify)
            except (ValueError, TypeError) as e:
                raise Exception('Bad syntax for Config File: (%s)%s' % (e, str(type(e))))
        else:
            conf = requests.get(config_arg, verify=False)
            self.config = json.loads(conf.text, object_hook=asciify)
            with open('hivecfg.json', 'w') as local_config:
                local_config.write(json.dumps(self.config, indent=4))

        Session.hive_id = self.config['general']['hive_id']

        if self.config['general']['fetch_ip']:
            try:
                url = 'http://api-sth01.exip.org/?call=ip'
                req = requests.get(url)
                self.hive_ip = req.text
                logging.info('Fetched {0} as external ip for Hive.'.format(self.hive_ip))
            except (Timeout, ConnectionError) as e:
                logging.warning('Could not fetch public ip: {0}'.format(e))

        else:
            self.hive_ip = self.config.get('general', 'hive_ip')

        self.status = {
            'mode': 'Hive',
            'ip_address': '127.0.0.1',  # Bad assumption?
            'hive_id': self.config['general']['hive_id'],
            'bees_sent': 0,
            'enabled_capabilities': [],
            'beekeeper_url': ''
        }

        #will contain HiveUser objects
        self.users = create_users()

        #inject authentication mechanism
        Session.authenticator = Authenticator(self.users)

        #spawning time checker
        if self.config['timecheck']['enabled']:
            Greenlet.spawn(self.checktime)

        #show curses UI
        if self.show_ui:
            self.uihandler = UIHandler(self.status)
            Greenlet.spawn(self.show_status_ui)

    def show_status_ui(self):
        self.uihandler.run()

    #function to check the time offset
    def checktime(self):
        """ Make sure our Hive time is consistent, and not too far off
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

        #will contain HiveStreamServer objects
        self.servers = []
        self.server_greenlets = []
        #will contain Session objects
        self.sessions = {}

        #greenlet to consume the provided sessions
        self.session_consumer = consumer.Consumer(self.sessions, self.hive_ip, self.config)
        Greenlet.spawn(self.session_consumer.start)

        #protocol handlers
        for c in handlerbase.HandlerBase.__subclasses__():

            cap_name = c.__name__

            if cap_name not in self.config['capabilities']:
                logger.warning(
                    "Not loading {0} capability because it has no option in configuration file.".format(c.__name__))
                continue
                #skip loading if disabled
            if not self.config['capabilities'][cap_name]['enabled']:
                continue

            port = self.config['capabilities'][cap_name]['port']
            #carve out the options for this specific service
            options = self.config['capabilities'][cap_name]
            cap = c(self.sessions, options, self.users, self.work_dir)

            try:
                socket = create_socket(('0.0.0.0', port))
                #Convention: All capability names which end in 's' will be wrapped in ssl.
                if cap_name.endswith('s'):
                    server = HiveStreamServer(socket, cap.handle_session,
                                              keyfile=self.key, certfile=self.cert)
                else:
                    server = HiveStreamServer(socket, cap.handle_session)

                self.servers.append(server)
                server_greenlet = Greenlet(server.start())
                self.server_greenlets.append(server_greenlet)

            except _socket.error as ex:
                logger.error("Could not start {0} server on port {1}. Error: {2}".format(c.__name__, port, ex))
            else:
                logger.info('Started {0} capability listening on port {1}'.format(c.__name__, port))

        drop_privileges()

        logger.info("Hive running - see log file (hive.log) for attack events.")
        gevent.joinall(self.server_greenlets)

    def stop(self):
        """Stops services"""
        for s in self.servers:
            s.stop()

        for g in self.server_greenlets:
            g.kill()

        self.uihandler.stop()
        self.session_consumer.stop()
        logger.info('All servers stopped.')

    @staticmethod
    def prepare_environment(work_dir):
        package_directory = os.path.dirname(os.path.abspath(beeswarm.__file__))

        logging.info('Copying data files to workdir.')
        shutil.copytree(os.path.join(package_directory, 'hive/data'), os.path.join(work_dir, 'data/'),
                        ignore=Hive._ignore_copy_files)

        #this config file is for standalone operations, it will be overwritten during __init__
        #if a config url is specified.
        config_file = os.path.join(work_dir, 'hivecfg.json.dist')
        if not os.path.isfile(config_file):
            logging.info('Copying configuration file to workdir.')
            shutil.copyfile(os.path.join(package_directory, 'hive/hivecfg.json.dist'),
                            os.path.join(work_dir, 'hivecfg.json'))

        create_self_signed_cert(work_dir, 'server.crt', 'server.key')

    @staticmethod
    def _ignore_copy_files(path, content):
        to_ignore = []
        for file_ in content:
            if file_ in ('.placeholder', '.git'):
                to_ignore.append(file_)
        return to_ignore


def create_users():
    """Creates the users for the Hive."""

    users = {}
    #TODO: Read from database or file
    username = 'test'
    password = 'test'
    users[username] = HiveUser(username, password)
    return users
