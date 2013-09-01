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
from OpenSSL import crypto

import urlparse
import os
import pwd
import grp
import platform
import logging
import _socket

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
    if platform.mac_ver()[0]:
        wanted_gid = -2
    else:
        wanted_gid = grp.getgrnam(gid_name)[2]

    os.setgid(wanted_gid)

    os.setuid(wanted_uid)

    new_uid_name = pwd.getpwuid(os.getuid())[0]
    new_gid_name = grp.getgrgid(os.getgid())[0]

    logger.info("Privileges dropped, running as {0}/{1}.".format(new_uid_name, new_gid_name))


def create_self_signed_cert(directory, cname, kname):
    logging.info('Creating SSL Certificate and Key: {}, {}'.format(cname, kname))
    pk = crypto.PKey()
    pk.generate_key(crypto.TYPE_RSA, 1024)

    cert = crypto.X509()
    sub = cert.get_subject()

    # Later, we'll get these fields from the BeeKeeper
    sub.C = 'US'
    sub.ST = 'Default'
    sub.L = 'Default'
    sub.O = 'Default Company'
    sub.OU = 'Default Org'
    sub.CN = _socket.gethostname()
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


def find_offset(fd, needle):
    """
        An implementation of the Horspool algorithm in python.
        Originally implemented by Kamran Khan (http://inspirated.com/about)
    """


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

    return -1
