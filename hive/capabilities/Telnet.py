from base import HandlerBase

class Telnet(HandlerBase):
	port = 23

	def handle(self, socket, address):
		#TODO: handle telnet meta communcation
		socket.sendall('Login: \r\n')

	
	def get_port(self):
		return Telnet.port

