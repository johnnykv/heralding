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
import struct
import urlparse
import os
import pwd
import grp
import platform
import logging
import socket
import json
import fcntl
import shutil

from OpenSSL import crypto
import netifaces
import zmq.green as zmq
import gevent
import requests
from beeswarm.shared.asciify import asciify

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
    logger.info('Creating SSL Certificate and Key.')
    pk = crypto.PKey()
    pk.generate_key(crypto.TYPE_RSA, 1024)

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
    priv_key_text = crypto.dump_privatekey(crypto.FILETYPE_PEM, pk)

    return cert_text, priv_key_text


def generate_cert_digest(str_cert):
    cert = crypto.load_certificate(crypto.FILETYPE_PEM, str_cert)
    return cert.digest('SHA256')


def find_offset(iso_file_path, needle):
    """
        An implementation of the Horspool algorithm in python.
        Originally implemented by Kamran Khan (http://inspirated.com/about)
    """

    with open(iso_file_path, 'r+b') as fd:
        nlen = len(needle)
        nlast = nlen - 1

        skip = []
        for k in range(256):
            skip.append(nlen)
        for k in range(nlast):
            skip[ord(needle[k])] = nlast - k
        skip = tuple(skip)

        pos = 0
        consumed = 0
        haystack = bytes()
        while True:
            more = nlen - (consumed - pos)
            morebytes = fd.read(more)
            haystack = haystack[more:] + morebytes

            if len(morebytes) < more:
                return -1
            consumed = consumed + more

            i = nlast
            while i >= 0 and haystack[i] == needle[i]:
                i = i - 1
            if i == -1:
                return pos

            pos = pos + skip[ord(haystack[nlast])]

        return None


def get_most_likely_ip():
    for interface_name in netifaces.interfaces():
        if interface_name.startswith('lo'):
            continue
        # TODO: continue if network interface is down
        addresses = netifaces.ifaddresses(interface_name)
        if netifaces.AF_INET in addresses:
            if 'addr' in addresses:
                logger.debug('Found likely IP {0} on IF {1}'.format(interface_name, addresses['addr']))
                return addresses['addr']

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
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(actor_url)
    socket.send(request)
    gevent.sleep()
    result = socket.recv()
    if result.split(' ', 1)[0] != Messages.OK:
        socket.close()
        assert False
    else:
        socket.close()
        return json.loads(result.split(' ', 1)[1])
    gevent.sleep()


def send_zmq_request_socket(socket, request):
    socket.send(request)
    result = socket.recv()
    if result.split(' ', 1)[0] != Messages.OK:
        assert False
    else:
        return json.loads(result.split(' ', 1)[1])


# for occasional zmq pushes
def send_zmq_push(actor_url, data):
    context = zmq.Context()
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


def extract_config_from_api(config_url):
    # meh, MiTM problem here... Acceptable? Workaround?
    # maybe print fingerprint on the web ui and let user verify manually?
    req = requests.get(config_url, verify=False)
    if req.status_code == 200:
        config = json.loads(req.text, object_hook=asciify)
        with open('beeswarmcfg.json', 'w') as local_config:
            local_config.write(json.dumps(config, indent=4))
        return True
    else:
        return False
