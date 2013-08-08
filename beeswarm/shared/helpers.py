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