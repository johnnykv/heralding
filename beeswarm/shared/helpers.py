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
from OpenSSL import crypto

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
import zmq.green as zmq

import beeswarm

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
    #special handling for os x. (getgrname has trouble with gid below 0)
    if platform.mac_ver()[0] and platform.mac_ver()[0] < float('10.9'):
        wanted_gid = -2
    else:
        wanted_gid = grp.getgrnam(gid_name)[2]

    os.setgid(wanted_gid)

    os.setuid(wanted_uid)

    new_uid_name = pwd.getpwuid(os.getuid())[0]
    new_gid_name = grp.getgrgid(os.getgid())[0]

    logger.info("Privileges dropped, running as {0}/{1}.".format(new_uid_name, new_gid_name))


def create_self_signed_cert(directory, cname, kname, cert_country='US', cert_state='state', cert_organization='org',
                            cert_locality='local', cert_organizational_unit='unit', cert_common_name='common name'):
    logger.info('Creating SSL Certificate and Key: {}, {}'.format(cname, kname))
    pk = crypto.PKey()
    pk.generate_key(crypto.TYPE_RSA, 1024)

    cert = crypto.X509()
    sub = cert.get_subject()

    # Later, we'll get these fields from the server
    # country
    sub.C = cert_country
    # state or province name
    sub.ST = cert_state
    # locality
    sub.L = cert_locality
    # organization
    sub.O = cert_organization
    # organizational unit
    sub.OU = cert_organizational_unit
    # common name
    sub.CN = cert_common_name

    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(365 * 24 * 60 * 60)  # Valid for a year
    cert.set_issuer(sub)
    cert.set_pubkey(pk)
    cert.sign(pk, 'sha1')

    certpath = os.path.join(directory, cname)
    keypath = os.path.join(directory, kname)

    with open(certpath, 'w') as certfile:
        certfile.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    priv_key_text = crypto.dump_privatekey(crypto.FILETYPE_PEM, pk)

    # We need to do this because Paramiko wants PKCS #1 RSA Key format.
    # I would really like to add a few swear words here.
    from Crypto.PublicKey import RSA

    priv_key = RSA.importKey(priv_key_text)
    with open(keypath, 'w') as keyfile:
        keyfile.write(priv_key.exportKey('PEM'))


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


# Shamelessly stolen from
# http://code.activestate.com/recipes/439094-get-the-ip-address-associated-with-a-network-inter/
def get_local_ipaddress(ifname):

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])


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
def send_command(actor_url, request):
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(actor_url)
    socket.send(request)
    result = socket.recv()
    if result.split(' ', 1)[0] != beeswarm.OK:
        logger.warning('Error while requesting config change to actor.')
        socket.close()
        assert(False)
    else:
        socket.close()
        return json.loads(result.split(' ', 1)[1])

def extract_keys(work_dir, config):
    #dump keys used for secure communication with beeswarm server
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
