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
import urlparse
import os
import pwd
import grp
import platform
import logging
import json
import shutil
import sys

from OpenSSL import crypto
from Crypto.PublicKey import RSA
import sqlalchemy as sa
from sqlalchemy.exc import ProgrammingError, OperationalError
from sqlalchemy.engine.url import make_url
from copy import copy


import netifaces
import zmq.green as zmq
import gevent
import requests
from beeswarm.shared.asciify import asciify
import beeswarm
import beeswarm.shared

from beeswarm.shared.message_enum import Messages


logger = logging.getLogger(__name__)


def is_url(string):
    parts = urlparse.urlsplit(string)
    if not parts.scheme or not parts.netloc:
        return False
    return True


def drop_privileges(uid_name='nobody', gid_name='nogroup'):
    if os.getuid() != 0:
        return

    wanted_uid = pwd.getpwnam(uid_name)[2]
    # special handling for os x. (getgrname has trouble with gid below 0)
    if platform.mac_ver()[0] and platform.mac_ver()[0] < float('10.9'):
        wanted_gid = -2
    else:
        wanted_gid = grp.getgrnam(gid_name)[2]

    os.setgid(wanted_gid)

    os.setuid(wanted_uid)

    new_uid_name = pwd.getpwuid(os.getuid())[0]
    new_gid_name = grp.getgrgid(os.getgid())[0]

    logger.info("Privileges dropped, running as {0}/{1}.".format(new_uid_name, new_gid_name))


def create_self_signed_cert(cert_country, cert_state, cert_organization, cert_locality, cert_organizational_unit,
                            cert_common_name):
    logger.info('Creating certificate and key.')
    rsa_key = RSA.generate(1024)
    pk = crypto.load_privatekey(crypto.FILETYPE_PEM, rsa_key.exportKey('PEM', pkcs=1))
    cert = crypto.X509()
    sub = cert.get_subject()
    sub.CN = cert_common_name
    sub.C = cert_country
    sub.ST = cert_state
    sub.L = cert_locality
    sub.O = cert_organization

    # optional
    if cert_organizational_unit:
        sub.OU = cert_organizational_unit

    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(365 * 24 * 60 * 60)  # Valid for a year
    cert.set_issuer(sub)
    cert.set_pubkey(pk)
    cert.sign(pk, 'sha1')

    cert_text = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
    priv_key_text = rsa_key.exportKey('PEM', pkcs=1)

    return cert_text, priv_key_text


def generate_cert_digest(str_cert):
    cert = crypto.load_certificate(crypto.FILETYPE_PEM, str_cert)
    return cert.digest('SHA256')


def get_most_likely_ip():
    for interface_name in netifaces.interfaces():
        if interface_name.startswith('lo'):
            continue
        # TODO: continue if network interface is down
        addresses = netifaces.ifaddresses(interface_name)
        if netifaces.AF_INET in addresses:
            for item in addresses[netifaces.AF_INET]:
                if 'addr' in item:
                    logger.debug('Found likely IP {0} on interface {1}'.format(item['addr'], interface_name))
                    return item['addr']
                    # well, actually the interface could have more IP's... But for now we assume that the IP
                    # we want is the first in the list on the IF.

    return '127.0.0.1'


def update_config_file(configfile, options):
    config = get_config_dict(configfile)

    with open(configfile, 'r+') as config_file:
        for k, v in options.items():
            config[k] = v
        config_file.seek(0)
        config_file.truncate(0)
        config_file.write(json.dumps(config, indent=4))


def get_config_dict(configfile):
    config = json.load(open(configfile, 'r'))
    return config


# for occasional req/resp
def send_zmq_request(actor_url, request):
    context = beeswarm.shared.zmq_context
    socket = context.socket(zmq.REQ)
    socket.connect(actor_url)
    socket.send(request)
    gevent.sleep()
    result = socket.recv()
    if result.split(' ', 1)[0] != Messages.OK.value:
        socket.close()
        assert False
    else:
        socket.close()
        return json.loads(result.split(' ', 1)[1])
    gevent.sleep()


def send_zmq_request_socket(socket, request):
    socket.send(request)
    result = socket.recv()
    status, data = result.split(' ', 1)
    if status != Messages.OK.value:
        logger.error('Receiving actor on socket {0} failed to respond properly. The request was: {1}'.format(socket,
                                                                                                             request))
        assert False
    else:
        if data.startswith('{') or data.startswith('['):
            return json.loads(result.split(' ', 1)[1])
        else:
            return data


# for occasional zmq pushes
def send_zmq_push(actor_url, data):
    context = beeswarm.shared.zmq_context
    socket = context.socket(zmq.PUSH)
    socket.connect(actor_url)
    socket.send(data)
    socket.close()
    gevent.sleep()


def extract_keys(work_dir, config):
    # dump keys used for secure communication with beeswarm server
    # safe to rm since we have everything we need in the config
    cert_path = os.path.join(work_dir, 'certificates')
    shutil.rmtree(cert_path, True)

    public_keys = os.path.join(cert_path, 'public_keys')
    private_keys = os.path.join(cert_path, 'private_keys')
    for _path in [cert_path, public_keys, private_keys]:
        if not os.path.isdir(_path):
            os.mkdir(_path)

    with open(os.path.join(public_keys, 'server.key'), 'w') as key_file:
        key_file.writelines(config['beeswarm_server']['zmq_server_public'])
    with open(os.path.join(public_keys, 'client.key'), 'w') as key_file:
        key_file.writelines(config['beeswarm_server']['zmq_own_public'])
    with open(os.path.join(private_keys, 'client.key'), 'w') as key_file:
        key_file.writelines(config['beeswarm_server']['zmq_own_private'])


def extract_config_from_api(config_url, config_file):
    # meh, MiTM problem here... Acceptable? Workaround?
    # maybe print fingerprint on the web ui and let user verify manually?
    try:
        req = requests.get(config_url, verify=False)
    except Exception as ex:
        logger.error('Error while extracting config: {0}'.format(ex))
        return None
    if req.status_code == 200:
        config = json.loads(req.text, object_hook=asciify)
        with open(config_file, 'w') as local_config:
            local_config.write(json.dumps(config, indent=4))
        return config
    else:
        return None


def stop_if_not_write_workdir(_dir):
    if not os.access(_dir, os.W_OK | os.X_OK):
        logger.error('Beeswarm needs write permisison to the work directory, '
                     'but did not have write permission to directory {0}.'.format(_dir))
        logger.debug('Current workdir: {0}, Asked dir: {1}'.format(os.getcwd(), _dir))
        logger.debug('Files in directory: {0}'.format(os.listdir(_dir)))
        sys.exit(1)
    for item in os.listdir(_dir):
        error = False
        if os.path.isfile(item):
            if not os.access(item, os.W_OK):
                error = True
        elif os.path.isdir(item):
            if not os.access(item, os.W_OK | os.X_OK):
                error = True
        if error:
            logger.error('Beeswarm needs write permisison to all files in the the work directory, '
                        'but did not have write permission to {0}.'.format(item))
            sys.exit(1)


# taken from sqlalchemy-utils
def database_exists(url):
    """Check if a database exists.

    :param url: A SQLAlchemy engine URL.

    Performs backend-specific testing to quickly determine if a database
    exists on the server. ::

        database_exists('postgres://postgres@localhost/name')  #=> False
        create_database('postgres://postgres@localhost/name')
        database_exists('postgres://postgres@localhost/name')  #=> True

    Supports checking against a constructed URL as well. ::

        engine = create_engine('postgres://postgres@localhost/name')
        database_exists(engine.url)  #=> False
        create_database(engine.url)
        database_exists(engine.url)  #=> True

    """

    url = copy(make_url(url))
    database = url.database
    if url.drivername.startswith('postgresql'):
        url.database = 'template1'
    else:
        url.database = None

    engine = sa.create_engine(url)

    if engine.dialect.name == 'postgresql':
        text = "SELECT 1 FROM pg_database WHERE datname='%s'" % database
        return bool(engine.execute(text).scalar())

    elif engine.dialect.name == 'mysql':
        text = ("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA "
                "WHERE SCHEMA_NAME = '%s'" % database)
        return bool(engine.execute(text).scalar())

    elif engine.dialect.name == 'sqlite':
        return database == ':memory:' or os.path.exists(database)

    else:
        text = 'SELECT 1'
        try:
            url.database = database
            engine = sa.create_engine(url)
            engine.execute(text)
            return True

        except (ProgrammingError, OperationalError):
            return False
