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

from handlerbase import HandlerBase
from datetime import datetime
import socket
import uuid

class telnet(HandlerBase):
	port = 2300
	#port = 23
	max_tries = 3

	def __init__(self, sessions):
		self.sessions = sessions

	def handle(self, gsocket, address):

		session = {'id' : uuid.uuid4(),
				   'timestamp' : datetime.utcnow(),
				   'last_activity' : datetime.utcnow(),
				   'attacker_ip' : address[0],
				   'attacker_src_port' : address[1],
				   'connected' : True,
				   'protocol_port' : telnet.port,
				   'protocol' : 'telnet',
				   'login_tries' : []}

		self.sessions[session['id']] = session

		banner = ''

		self.send_message(session, gsocket, banner)

		self.send_message(session, gsocket, "login: ")

		data = []
		telnet_state = ''
		prompt_state = 'login'
		attempts = 0;

		while attempts < telnet.max_tries:

			try:
				read = gsocket.recv(1)
			except socket.error, (value, message):
				session['connected'] = False
				break

			session['last_activity'] = datetime.utcnow()
			
			if telnet_state == '':
				if ord(read) == 255:
					data.append(read)
					telnet_state = 'iac'
				elif ord(read) == 250: #start negotiation (SB)
					data.append(read)
					telnet_state = 'negotiation'
				else:
					data.append(read)
					if len(data) > 1:
						if data[-1] == '\n' and data[-2] == '\r':
							if prompt_state == 'login':
								login = ''.join(data)[:-2]
								self.send_message(session, gsocket, "Password: ")
								data = []
								prompt_state = 'password'
							else:
								session['login_tries'].append({'login' : login, 'password' : ''.join(data)[:-2], 'id' : uuid.uuid4(), 'timestamp' : datetime.utcnow() })
								attempts += 1
								data = []
								self.send_message(session, gsocket, 'Invalid username/password.\r\n')
								prompt_state = 'login'
								data = []
								if attempts < telnet.max_tries:
									self.send_message(session, gsocket, "login: ")
			elif telnet_state == 'negotiation':
				if ord(read) == 240: #end of negotiation (SE)
					data.append(read)
					self.parse_cmd(session, gsocket, data)
					telnet_state = ''
					data = []
			elif telnet_state == 'iac':
				if ord(read) in (241, 242, 243, 244, 245, 246, 247, 248, 249): #single command
					data.append(read)
					self.parse_cmd(session, gsocket, data)
					telnet_state = ''
					data = []
				elif ord(read) in (251, 252, 253, 254): #will, wont, do, dont
					telnet_state = 'command'
					data.append(read)
			elif telnet_state == 'command':
				data.append(read)
				self.parse_cmd(session, gsocket, data)
				telnet_state = ''
				data = []

		session['connected'] = False
		
	def get_port(self):
		return telnet.port
		
	def parse_cmd(self, session, gsocket, data):
		print "Command received:"
		print data

	def send_message(self, session, gsocket, msg):
		try:
			gsocket.sendall(msg)
		except socket.error, (value, msg):
				session['connected'] = False

