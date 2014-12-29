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

# Functions in this file provides functionality to bootstrap a beeswarn server
# and a drone running both running on localhost

import os
import logging
from argparse import ArgumentParser
import json

import zmq.green as zmq
import gevent
import beeswarm
from beeswarm.server.db import database_setup

from beeswarm.server.db.entities import Honeypot
from beeswarm.server.server import Server
from beeswarm.shared.socket_enum import SocketNames
from beeswarm.shared.message_enum import Messages
from beeswarm.shared.helpers import send_zmq_request_socket


logger = logging.getLogger()


def bootstrap(server_workdir, drone_workdir):
    """Bootstraps localhost configurations for a Beeswarm server and a honeypot.

    :param server_workdir: Output directory for the server configuration file.
    :param drone_workdir: Output directory for the drone configuration file.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)-15s (%(name)s) %(message)s')

    console_log = logging.StreamHandler()
    console_log.setLevel(logging.INFO)
    console_log.setFormatter(formatter)
    root_logger.addHandler(console_log)

    server_workdir_absolute = os.path.abspath(server_workdir)
    old_cwd = os.getcwd()
    os.chdir(server_workdir)
    server = Server(server_workdir_absolute, None, start_webui=False, customize=False, reset_password=False,
                    max_sessions=0, server_hostname='127.0.0.1')
    logger.info('Server config has been written to {0}'.format(os.path.join(server_workdir, 'beeswarmcfg.json')))
    gevent.spawn(server.start, False)
    # waiting game to ensure actors has started.
    gevent.sleep(2)
    os.chdir(old_cwd)

    # setting up socket to communicate with ZMQ actor.
    context = beeswarm.shared.zmq_context
    database_actor = context.socket(zmq.REQ)
    database_actor.connect(SocketNames.DATABASE_REQUESTS.value)

    db_session = database_setup.get_session()
    drone = Honeypot()

    protocol_config = (
        ('ftp', 21, {
            'max_attempts': 3,
            'banner': 'Microsoft FTP Server',
            'syst_type': 'Windows-NT'
        }),
        ('telnet', 23, {
            'max_attempts': 3
        }),
        ('pop3', 110, {
            'max_attempts': 3
        }),
        ('pop3s', 993, {
            'max_attempts': 3
        }),
        ('ssh', 22, {}),
        ('http', 80, {
            'banner': 'Microsoft-IIS/5.0'
        }),
        ('https', 443, {
            'banner': 'Microsoft-IIS/5.0'
        }),
        ('smtp', 25, {
            'banner': 'Microsoft ESMTP MAIL service ready'
        }),
        ('vnc', 5900, {})
    )

    for protocol, port, protocol_specific_data in protocol_config:
        drone.add_capability(protocol, port, protocol_specific_data)

    drone.cert_common_name = '*'
    drone.cert_country = 'US'
    drone.cert_state = 'None'
    drone.cert_locality = 'None'
    drone.cert_organization = 'None'
    drone.cert_organization_unit = ''

    db_session.add(drone)
    db_session.commit()
    drone_config = send_zmq_request_socket(database_actor, '{0} {1}'.format(Messages.DRONE_CONFIG.value, drone.id))

    with open(os.path.join(drone_workdir, 'beeswarmcfg.json'), 'w') as drone_config_file:
        drone_config_file.write(json.dumps(drone_config, indent=4))
    logger.info('Drone config has been written to {0}'.format(os.path.join(server_workdir, 'beeswarmcfg.json')))

    server.stop()


if __name__ == '__main__':
    parser = ArgumentParser(description='Beeswarm localhost bootstrapper')

    parser.add_argument('server_workdir', help='Output directory for the server configuration file.')
    parser.add_argument('drone_workdir', help='Output directory for the drone configuration file.')

    args = parser.parse_args()
    bootstrap(args.server_workdir, args.drone_workdir)

