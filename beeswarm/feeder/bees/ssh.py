# Copyright (C) 2013 Aniket Panse <contact@aniketpanse.in>
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
import logging
import random

from beeswarm.feeder.bees.clientbase import ClientBase


class ssh(ClientBase):

    def __init__(self, sessions, options):
        super(ssh, self).__init__(sessions, options)
        self.client = None
        self.command_count = 0
        self.command_limit = random.randint(6, 11)

    def do_session(self, my_ip):
        login = self.options['login']
        password = self.options['password']
        server_host = self.options['server']
        server_port = self.options['port']
        session = self.create_session(login, password, server_host, server_port, my_ip)

        self.sessions[session.id] = session
        logging.debug(
            'Sending %s honeybee to %s:%s. (bee id: %s)' % ('ssh', server_host, server_port, session.id))

        print 'RUNNING SSH SESSION'