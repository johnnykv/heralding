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

from beeswarm.drones.client.models.session import BaitSession


class ClientBase(object):
    """ Base class for Bees. This should only be used after sub-classing. """

    def __init__(self, sessions, options):
        """
            Initializes common values.
        :param sessions: A dict which is updated every time a new session is created.
        :param options: A dict containing the options entry for this bait
        """
        self.sessions = sessions
        self.options = options

    def start(self, my_ip):
        raise Exception('Do not call base class!')

    def create_session(self, server_host, server_port, honeypot_id):
        """
            Creates a new session and adds it to the sessions directory.

        :param server_host: IP address of the server
        :param server_port: Server port
        :return: A new `BeeSession` object.
        """
        protocol = self.__class__.__name__.lower()
        session = BaitSession(protocol, server_host, server_port, honeypot_id)
        self.sessions[session.id] = session
        return session
