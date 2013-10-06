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
import json

import logging
import os
import shutil

import gevent
from gevent.pywsgi import WSGIServer
import beeswarm
from beeswarm.beekeeper.db import database
from beeswarm.beekeeper.webapp import app
from beeswarm.beekeeper.webapp.auth import Authenticator
from beeswarm.shared.helpers import drop_privileges
from beeswarm.beekeeper.misc.scheduler import Scheduler
from beeswarm.shared.helpers import find_offset, create_self_signed_cert, update_config_file

logger = logging.getLogger(__name__)


class Beekeeper(object):
    def __init__(self, work_dir, config_arg='beekeepercfg.json', curses_screen=None):
        """
            Main class for the Beekeeper Web-Interface. It takes care of setting up
            the database, managing the users, etc.

        :param work_dir: The working directory (usually the current working directory).
        :param config_arg: Specifies the name of the config file.
        :param curses_screen: This parameter is to maintain a similar interface for
                               all the modes. It is ignored for the Beekeeper.
        """
        self.work_dir = work_dir
        self.config_file = config_arg
        self.config = self.get_config(self.config_file)

        self.servers = {}
        self.greenlets = []
        self.started = False

        database.setup_db(os.path.join(self.config['sql']['connection_string']))
        self.app = app.app
        self.app.config['CERT_PATH'] = self.config['ssl']['certpath']
        self.app.config['BEEKEEPER_CONFIG'] = self.config_file
        self.authenticator = Authenticator()
        self.authenticator.ensure_default_user()

    def start(self, port=5000, maintenance=True):
        """
            Starts the Beekeeper web-app on the specified port.
            Beekeeper is the maintenance interface.

        :param port: The port on which the web-app is to run.
        """
        self.started = True
        logger.info('Starting Beekeeper listening on port {0}'.format(port))

        http_server = WSGIServer(('', 5000), self.app, keyfile='beekeeper.key', certfile='beekeeper.crt')
        http_server_greenlet = gevent.spawn(http_server.serve_forever)
        self.servers['http'] = http_server
        self.greenlets.append(http_server_greenlet)

        if maintenance:
            maintenance_greenlet = gevent.spawn(self.start_maintenance_tasks)
            self.servers['maintenance'] = maintenance_greenlet
            self.greenlets.append(maintenance_greenlet)

        drop_privileges()
        gevent.joinall(self.greenlets)

    def stop(self):
        """
            Stops the web-app.
        """
        self.started = False
        logging.info('Stopping beekeeper.')
        self.servers['http'].stop(5)

    def get_config(self, configfile):
        """
            Loads the configuration from the JSON file, and returns it.
        :param configfile: Path to the configuration file
        """
        with open(configfile) as config_file:
            config = json.load(config_file)
        return config

    def start_maintenance_tasks(self):
        # one-off task to ensure we have the correct offset

        logger.info('Hang on, calculating binary offset - this can take a while!')
        if os.path.isfile(self.config['iso']['path']):
            config_tar_offset = find_offset(self.config['iso']['path'], '\x07' * 30)

            if not config_tar_offset:
                logger.warning('Beekeeper client ISO was found but is invalid. Bootable clients can not be generated.')
                raise Exception('Expected binary pattern not found in ISO file.')
            else:
                logger.debug('Binary pattern found in ISO at: {0}'.format(config_tar_offset))
                with open(self.config_file, 'r+') as config_file:
                    self.config['iso']['offset'] = config_tar_offset
                    #clear file
                    config_file.seek(0)
                    config_file.truncate(0)
                    # and  write again
                    config_file.write(json.dumps(self.config, indent=4))
        else:
            logger.warning('Beekeeper client ISO was NOT found. Bootable clients can not be generated.')

        maintenance_worker = Scheduler(self.config)
        maintenance_greenlet = gevent.spawn(maintenance_worker.start)

        config_last_modified = os.stat(self.config_file).st_mtime
        while self.started:
            poll_last_modified = os.stat(self.config_file).st_mtime
            if poll_last_modified > config_last_modified:
                logger.debug('Config file changed, restarting maintenance workers.')
                config_last_modified = poll_last_modified
                config = self.get_config(self.config_file)

                #kill and stop old greenlet
                maintenance_worker.stop()
                maintenance_greenlet.kill(timeout=2)

                #spawn new worker greenlet and pass the new config
                maintenance_worker = Scheduler(config)
                maintenance_greenlet = gevent.spawn(maintenance_worker.start)

            #check config file for changes every 5 second
            gevent.sleep(5)

    @staticmethod
    def prepare_environment(work_dir):
        package_directory = os.path.dirname(os.path.abspath(beeswarm.__file__))
        config_file = os.path.join(work_dir, 'beekeepercfg.json')
        if not os.path.isfile(config_file):
            logging.info('Copying configuration file to workdir.')
            print '*** Please answer a few configuration options ***'
            print ''
            print '* Certificate Information *'
            print 'IMPORTANT: Please make sure that "Common Name" is the IP address or fully qualified host name ' \
                  ' that you want to use for the beekeeper API.'
            cert_cn = raw_input('Common Name: ')
            cert_country = raw_input('Country: ')
            cert_state = raw_input('State: ')
            cert_locality = raw_input('Locality/City: ')
            cert_org = raw_input('Organization: ')
            cert_org_unit = raw_input('Organizational unit: ')
            print ''
            print '* Network *'
            tcp_port = raw_input('Port for UI/API (default: 5000): ')
            if tcp_port:
                tcp_port = int(tcp_port)
            else:
                tcp_port = 5000
            # to keep things simple we just use the CN for host for now.
            tcp_host = cert_cn

            create_self_signed_cert(work_dir, 'beekeeper.crt', 'beekeeper.key', cert_country, cert_state, cert_org,
                                    cert_locality, cert_org_unit, cert_cn)

            shutil.copyfile(os.path.join(package_directory, 'beekeeper/beekeepercfg.json.dist'),
                            config_file)

            # update the config file
            update_config_file(config_file, {'network': {'port': tcp_port, 'host': tcp_host}})


