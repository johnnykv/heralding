# Copyright (C) 2012 Johnny Vestergaard <jkv@unixcluster.dk>
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

import poplib
from clientbase import ClientBase
from datetime import datetime
import uuid

class pop3(ClientBase):

	def __init__(self, sessions):
		self.sessions = sessions

	def do_session(self, login, password, server_host, server_port):
		"""Login, RETR and DELE all messages"""

		session = {
				   'id' : uuid.uuid4(),
				   'protocol' : 'pop3',
				   'login' : login,
				   'password' : password,
				   'server_host' : server_host,
				   'server_port' : server_port,
				   'timestamp' : datetime.utcnow(),
				   'did_connect' : False,
				   'did_login' : False,
				   'protocol_data' : {}
				   }

		self.sessions.append(session)

		try:
			conn = poplib.POP3(server_host, server_port)
			banner = conn.getwelcome()
			session['protocol_banner'] = banner
			session['did_connect'] = True
			
			conn.user(login)
			conn.pass_(password)
			session['did_login'] = True
			session['timestamp'] = datetime.utcnow()
		except poplib.error_proto:
			pass
		else:
			list_entries = conn.list()[1]
			for entry in list_entries:
				index, octets = entry.split(' ')
				conn.retr(index)
				conn.dele(index)
			conn.quit()
			session['did_complete'] = True
			