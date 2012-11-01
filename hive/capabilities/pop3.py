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

		state = 'AUTHORIZATION'

		session = {'id' : uuid.uuid4(),
				   'timestamp' : datetime.utcnow(),
				   'last_activity' : datetime.utcnow(),
				   'socket' : gsocket,
				   'address' : address,
				   'connected' : True,
				   'protocol' : 'pop3',
				   'login_tries' : []}

		self.sessions[session['id']] = session

		#just because of readline... tsk tsk...
		fileobj = gsocket.makefile()

		self.send_message(session, '+OK POP3 server ready')

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
					self.auth_apop(session, msg)
				elif cmd == 'USER':
					self.cmd_user(session, msg)
				elif cmd == 'PASS':
					self.cmd_pass(session, msg)
				else:
					self.send_message(session, '-ERR Unknown command')
			#at the moment we dont handle TRANSACTION state...
			elif state == 'TRANSACTION':
				if cmd == 'STAT':
					self.not_impl(session, msg)
				elif cmd == 'LIST':
					self.not_impl(session, msg)
				elif cmd == 'RETR':
					self.not_impl(session, msg)
				elif cmd == 'DELE':
					self.not_impl(session, msg)
				elif cmd == 'NOOP':
					self.not_impl(session, msg)
				elif cmd == 'RSET':
					self.not_impl(session, msg)
				else:
					self.send_message(session, '-ERR Unknown command')
			else:
				raise Exception('Unknown state: ' + session['state'])

	#APOP mrose c4c9334bac560ecc979e58001b3e22fb
	#+OK mrose's maildrop has 2 messages (320 octets)
	def auth_apop(self, session, msg):
		raise Exception('Not implemented yet!')

	#USER mrose
	#+OK User accepted
	#PASS tanstaaf
	#+OK Pass accepted
	#or: "-ERR Authentication failed."
	#or: "-ERR No username given."
	def cmd_user(self, session, msg):
		session['USER'] = msg #TODO: store USER somewhere else
		self.send_message(session, '+OK User accepted')

	def cmd_pass(self, session, msg):
		if 'USER' not in session:
			self.send_message(session, '-ERR No username given.')
		else:
			session['password'] = msg
			self.send_message(session, "-ERR Authentication failed.")
			session['login_tries'].append({'login' : session['USER'], 'password' : msg})
			del session['USER']
		
	def get_port(self):
		return pop3.port

	def not_impl(self, session, msg):
		raise Exception('Not implemented yet!')

	def send_message(self, session, msg):
		try:
			session['socket'].sendall(msg + "\r\n")
		except socket.error, (value, msg):
				session['connected'] = False

