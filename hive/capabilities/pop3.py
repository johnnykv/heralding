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
from gevent.server import StreamServer
import socket
import uuid
import json

class pop3(HandlerBase):
	port = 2100
	max_tries = 10
	#port = 110
	cmds = {}

	def __init__(self, sessions, accounts):
		self.sessions = sessions

		#to make the honeypot look legit we need to main a global mainspool state
		self.mailspools = {}
		self.accounts = accounts

	def handle(self, gsocket, address):
		state = 'AUTHORIZATION'

		session = {'id' : uuid.uuid4(),
				   'timestamp' : datetime.utcnow(),
				   'last_activity' : datetime.utcnow(),
				   'attacker_ip' : address[0],
				   'attacker_src_port' : address[1],
				   'connected' : True,
				   'protocol_port' : pop3.port,
				   'protocol' : 'pop3',
				   'login_tries' : [],
				   'deleted_index' : []}

		self.sessions[session['id']] = session

		#just because of readline... tsk tsk...
		fileobj = gsocket.makefile()

		self.send_message(session, gsocket, '+OK POP3 server ready')

		while state != '' and session['connected']:
			try:
				raw_msg = fileobj.readline()
			except socket.error, (value, message):
				session['connected'] = False
				break

			session['last_activity'] = datetime.utcnow()

			msg = None

			if ' ' in raw_msg:
				cmd, msg = raw_msg.rstrip().split(' ', 1)
			else:
				cmd = raw_msg.rstrip()
			cmd = cmd.lower()

			func_to_call = getattr(self, 'cmd_%s' % cmd, None)
			if func_to_call is None or not self.is_state_valid(state, cmd):
				self.send_message(session, gsocket, '-ERR Unknown command')
			else:
				return_value = func_to_call(session, gsocket, msg)
				#state changers!
				if state == 'AUTHORIZATION' or cmd == 'quit':
					state = return_value

		session['connected'] = False

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
		return 'AUTHORIZATION'

	def is_state_valid(self, state, cmd):
		if state == 'AUTHORIZATION':
			if cmd in ['apop', 'user', 'pass', 'quit']:
				return True;
		elif state == 'TRANSACTION':
			if cmd in ['list', 'retr', 'dele', 'noop', 'stat', 'rset', 'quit']:
				return True
		return False

	def cmd_pass(self, session, gsocket, msg):
		if 'USER' not in session:
			self.send_message(session, gsocket, '-ERR No username given.')
		else:
			#session['password'] = msg
			session['login_tries'].append({'login' : session['USER'], 'password' : msg, 'id' : uuid.uuid4(), 'timestamp' : datetime.utcnow() })
			
			if session['USER'] in self.accounts: # checking username
				if self.accounts[session['USER']] == msg: # checking password
					self.send_message(session, gsocket, "+OK Pass accepted")
					if session['USER'] not in self.mailspools:
						self.get_mailspool(session['USER'])
					return 'TRANSACTION'

		self.send_message(session, gsocket, "-ERR Authentication failed.")
		if 'USER' in session:
			del session['USER']
		return 'AUTHORIZATION'
		
	def cmd_noop(self, session, gsocket, msg):
		self.send_message(session, gsocket, '+OK')

	def cmd_retr(self, session, gsocket, msg):

		user_mailspool = self.mailspools[session['USER']]

		try:
			index = int(msg) - 1
		except ValueError:
			self.send_message(session, gsocket, '-ERR no such message')
		else:
			if index < 0 or len(user_mailspool) < index:
				self.send_message(session, gsocket, '-ERR no such message')
			else:
				msg = '+OK %i octets' % (len(user_mailspool[index]))
				self.send_message(session, gsocket, msg)
				self.send_data(session, gsocket, user_mailspool[index])

	def cmd_dele(self, session, gsocket, msg):
		
		user_mailspool = self.mailspools[session['USER']]

		try:
			index = int(msg) - 1
		except ValueError:
			self.send_message(session, gsocket, '-ERR no such message')
		else:
			if index < 0 or len(user_mailspool) <= index:
				self.send_message(session, gsocket, '-ERR no such message')
			else:
				if index in session['deleted_index']:
					reply = '-ERR message %s already deleted' % (msg)
					self.send_message(session, gsocket, reply)
				else:
					session['deleted_index'].append(index)
					reply = '+OK message %s deleted' % (msg)
					self.send_message(session, gsocket, reply)


	def cmd_stat(self, session, gsocket, msg):

		user_mailspool = self.mailspools[session['USER']]
		mailspool_bytes_size = 0
		mailspool_num_messages = 0

		for index, value in enumerate(user_mailspool):
			if index not in session['deleted_index']: # ignore deleted messages
				mailspool_bytes_size += len(value)
				mailspool_num_messages += 1

		reply = '+OK %i %i' % (mailspool_num_messages, mailspool_bytes_size)

		self.send_message(session, gsocket, reply)

	def cmd_quit(self, session, gsocket, msg):
		self.send_message(session, gsocket, '+OK Logging out')
		return ''

	def cmd_list(self, session, gsocket, argument):

		user_mailspool = self.mailspools[session['USER']]
		
		if argument is None:
			mailspool_bytes_size = 0
			mailspool_num_messages = 0

			for index, value in enumerate(user_mailspool):
				if index not in session['deleted_index']: # ignore deleted messages
					mailspool_bytes_size += len(value)
					mailspool_num_messages += 1
			
			reply = "+OK %i messages (%i octets)" % (mailspool_num_messages, mailspool_bytes_size)
			self.send_message(session, gsocket, reply)

			for index, value in enumerate(user_mailspool):
				if index not in session['deleted_index']: # ignore deleted messages
					reply = "%i %i" % (index + 1, len(value))
					self.send_message(session, gsocket, reply)
		else:
			index = int(argument) - 1
			if index < 0 or len(user_mailspool) < index or index in session['deleted_index']:
				reply = '-ERR no such message'
				self.send_message(session, gsocket, reply)
			else:
				mail = user_mailspool[index]
				reply = '+OK %i %i' % (index + 1, len(mail))
				self.send_message(session, gsocket, reply)

	def get_port(self):
		return pop3.port

	def not_impl(self, session, gsocket, msg):
		raise Exception('Not implemented yet!')

	def send_message(self, session, gsocket, msg):
		try:
			gsocket.sendall(msg + "\n")
		except socket.error, (value, msg):
				session['connected'] = False

	def send_data(self, session, gsocket, data):
		try:
			gsocket.sendall(data)
		except socket.error, (value, msg):
				session['connected'] = False

	#TODO: Dynamically fetch and modify new content (which looks legit...)
	def get_mailspool(self, username):
		try:
			user_spool = json.load(open('./capabilities/mails.json')).values()
			self.mailspools[username] = user_spool
		except IOError:
			user_spool = []
