from base import HandlerBase
import uuid

class pop3(HandlerBase):
	port = 2100
	#port = 110

	def handle(self, socket, address):

		session = {'id' : uuid.uuid4(),
				   'state' : 'AUTHORIZATION',
				   'socket' : socket}

		#just because of readline... tsk tsk...
		fileobj = socket.makefile()
		session['fileobj'] = fileobj

		socket.sendall('+OK POP3 server ready\r\n')

		while True:
			print session
			raw_msg = fileobj.readline()
			if ' ' in raw_msg:
				cmd, msg = raw_msg.replace('\r\n', '').split(' ', 1)
			else:
				cmd = raw_msg

			if session['state'] == 'AUTHORIZATION':
				if cmd == 'APOP':
					self.auth_apop(session, msg)
				elif cmd == 'USER':
					self.cmd_user(session, msg)
				elif cmd == 'PASS':
					self.cmd_pass(session, msg)
				else:
					socket.sendall('-ERR Unknown command\r\n')
			elif session['state'] == 'TRANSACTION':
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
					socket.sendall('-ERR Unknown command\r\n')
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
		session['USER'] = msg
		session['socket'].sendall('+OK User accepted\r\n')

	def cmd_pass(self, session, msg):
		if 'USER' not in session:
			session['socket'].sendall('-ERR No username given.\r\n')
		else:
			session['password'] = msg
		
	def get_port(self):
		return pop3.port

	def not_impl(self, session, msg):
		raise Exception('Not implemented yet!')
