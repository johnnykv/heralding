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

class pop3(HandlerBase):
	port = 2100
	max_tries = 10
	#port = 110

	def __init__(self, sessions):
		self.sessions = sessions

	def handle(self, gsocket, address):
		print address
		state = 'AUTHORIZATION'

		session = {'id' : uuid.uuid4(),
				   'timestamp' : datetime.utcnow(),
				   'last_activity' : datetime.utcnow(),
				   'attacker_ip' : address[0],
				   'attacker_src_port' : address[1],
				   'connected' : True,
				   'protocol_port' : pop3.port,
				   'protocol' : 'pop3',
				   'login_tries' : []}

		self.sessions[session['id']] = session

		#just because of readline... tsk tsk...
		fileobj = gsocket.makefile()

		self.send_message(session, gsocket, '+OK POP3 server ready')

		while True:
			try:
				raw_msg = fileobj.readline()
			except socket.error, (value, message):
				session['connected'] = False
				break

			session['last_activity'] = datetime.utcnow()

			if ' ' in raw_msg:
				cmd, msg = raw_msg.replace('\r\n', '').split(' ', 1)
			else:
				cmd = raw_msg

			if state == 'AUTHORIZATION':
				if cmd == 'APOP':
					self.auth_apop(session, gsocket, msg)
				elif cmd == 'USER':
					self.cmd_user(session, gsocket,  msg)
				elif cmd == 'PASS':
					self.cmd_pass(session, gsocket,  msg)
				else:
					self.send_message(session, gsocket, '-ERR Unknown command')
			#at the moment we dont handle TRANSACTION state...
			elif state == 'TRANSACTION':
				if cmd == 'STAT':
					self.not_impl(session, gsocket,  msg)
				elif cmd == 'LIST':
					self.not_impl(session, gsocket,  msg)
				elif cmd == 'RETR':
					self.not_impl(session, gsocket,  msg)
				elif cmd == 'DELE':
					self.not_impl(session, gsocket,  msg)
				elif cmd == 'NOOP':
					self.not_impl(session, gsocket,  msg)
				elif cmd == 'RSET':
					self.not_impl(session, gsocket,  msg)
				else:
					self.send_message(session, gsocket, '-ERR Unknown command')
			else:
				raise Exception('Unknown state: ' + session['state'])

	#APOP mrose c4c9334bac560ecc979e58001b3e22fb
	#+OK mrose's maildrop has 2 messages (320 octets)
	def auth_apop(self, session, gsocket, msg):
		raise Exception('Not implemented yet!')

	#USER mrose
	#+OK User accepted
	#PASS tanstaaf
	#+OK Pass accepted
	#or: "-ERR Authentication failed."
	#or: "-ERR No username given."
	def cmd_user(self, session, gsocket, msg):
		session['USER'] = msg #TODO: store USER somewhere else
		self.send_message(session, gsocket, '+OK User accepted')

	def cmd_pass(self, session, gsocket, msg):
		if 'USER' not in session:
			self.send_message(session, gsocket, '-ERR No username given.')
		else:
			session['password'] = msg
			self.send_message(session, gsocket, "-ERR Authentication failed.")
			session['login_tries'].append({'login' : session['USER'], 'password' : msg, 'id' : uuid.uuid4(), 'timestamp' : datetime.utcnow() })
			del session['USER']
		
	def get_port(self):
		return pop3.port

	def not_impl(self, session, gsocket, msg):
		raise Exception('Not implemented yet!')

	def send_message(self, session, gsocket, msg):
		try:
			gsocket.sendall(msg + "\r\n")
		except socket.error, (value, msg):
				session['connected'] = False

