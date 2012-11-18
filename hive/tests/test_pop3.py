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

import sys
sys.path.append('../') #to be able to import capabilities

from gevent.server import StreamServer
import gevent
import unittest
from capabilities import pop3
import uuid
from datetime import datetime
from datetime import timedelta

class Pop3_Tests(unittest.TestCase):

	def test_sessionkeys(self):
		"""Tests if the session dict initially contains the correct keys"""

		sessions = {}
		accounts = {}
		sut = pop3.pop3(sessions, accounts)

		#dont really care about the socket at this point (None...)
		#TODO: mock the socket!
		try:
			sut.handle(None, ['192.168.1.200', 51000])
		except:
			pass

		session = sessions[sessions.keys()[0]]
		self.assertTrue(len(str(session['id'])) > 20)
		
		delta = datetime.utcnow() - session['timestamp']
		self.assertTrue(delta.seconds < 2)

		delta = datetime.utcnow() - session['last_activity']
		self.assertTrue(delta.seconds < 2)

		self.assertTrue(session['attacker_ip'] == '192.168.1.200')
		self.assertTrue(session['attacker_src_port'] == 51000)

		#just check that we have the keys
		self.assertTrue('connected' in session)
		self.assertTrue('login_tries' in session)

		self.assertEqual(session['protocol'], 'pop3')
		self.assertEqual(session['protocol_port'], pop3.pop3.port)

	def test_login(self):
		"""Testing different login combinations"""

		login_sequences = [
			#valid login. valid password
			(('USER james', '+OK User accepted'), ('PASS bond', '+OK Pass accepted')),
			#valid login, invalid password
			(('USER james', '+OK User accepted'), ('PASS wakkawakka', '-ERR Authentication failed.')),
			#invalid login, invalid password
			(('USER wakkwakk', '+OK User accepted'), ('PASS wakkwakk', '-ERR Authentication failed.')),
			#PASS without user
			(('PASS bond', '-ERR No username given.'),),
		]

		sessions = {}
		accounts = {'james' : 'bond'}
		sut = pop3.pop3(sessions, accounts)

		server = StreamServer(('127.0.0.1', 0), sut.handle)
		server.start()
		for sequence in login_sequences:
			client = gevent.socket.create_connection(('127.0.0.1', server.server_port))
			
			fileobj = client.makefile()

			#skip banner
			fileobj.readline()
			for pair in sequence:
				client.sendall(pair[0] + "\r\n")
				response = fileobj.readline().rstrip()
				print pair
				self.assertEqual(response, pair[1])
				#assert response == pair[1]

		
if __name__ == '__main__':
	unittest.main()