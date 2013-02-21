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

from hive.models.session import Session


class HandlerBase(object):
    def __init__(self, sessions, port):
        self.sessions = sessions
        #serviceport
        self.port = port

    def create_session(self, address):
        protocol = self.__class__.__name__
        session = Session(address[0], address[1], protocol)
        session.honey_port = self.port
        self.sessions[session.id] = session
        return session

    def handle_session(self, socket, address):
        raise Exception('Do no call base class!')

