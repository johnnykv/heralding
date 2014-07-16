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

import os
import logging

from fs.osfs import OSFS

from beeswarm.drones.honeypot.models.session import Session


logger = logging.getLogger(__name__)


class HandlerBase(object):
    def __init__(self, sessions, options, workdir):
        """
        Base class that all capabilities must inherit from.

        :param sessions: a dictionary of Session objects.
        :param options: a dictionary of configuration options.
        :param workdir: the directory which contains files for this
                        particular instance of Beeswarm
        """
        self.sessions = sessions
        self.options = options
        if 'users' in options:
            self.users = options['users']
        else:
            self.users = {}
        # virtual file system shared by all capabilities
        self.vfsystem = OSFS(os.path.join(workdir, 'data/vfs'))
        # serviceport
        self.port = int(options['port'])

    def create_session(self, address, socket):
        protocol = self.__class__.__name__.lower()
        session = Session(address[0], address[1], protocol, socket, self.users)
        session.destination_port = self.port
        self.sessions[session.id] = session
        logger.info('Accepted {0} session on port {1} from {2}:{3}. ({4})'.format(protocol, self.port, address[0],
                                                                                  address[1], str(session.id)))
        return session

    def handle_session(self, socket, address):
        raise Exception('Do no call base class!')
