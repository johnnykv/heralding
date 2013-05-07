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

from datetime import datetime

from gevent.ssl import SSLSocket


class HiveSSLSocket(SSLSocket):
    """
    Provides timings to the socket class.
    """

    def __init__(self, *args, **kwargs):
        super(HiveSSLSocket, self).__init__(*args, **kwargs)
        self.last_activity = datetime.now()

    def recv(self, *args):
        self.last_activity = datetime.now()
        return super(HiveSSLSocket, self).recv(*args)

    def recvfrom(self, *args):
        self.last_activity = datetime.now()
        return super(HiveSSLSocket, self).recvfrom(*args)

    def recvfrom_into(self, *args):
        self.last_activity = datetime.now()
        return super(HiveSSLSocket, self).recvfrom_into(*args)

    def last_update(self):
        """
        Returns seconds since the last time the socket was asked to receive data.
        """
        return (datetime.now() - self.last_activity).seconds
