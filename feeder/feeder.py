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

#hmm... right here?
from bees import clientbase
from bees import pop3
import gevent

def main():
	#TODO: Read this from configuration file or commandline arguments
	# enabled_clients = ['pop3', ]

	# #greenlet to consume and maintain data in sessions list
	# sessions_consumer = consumer.Consumer(sessions)
	# Greenlet.spawn(sessions_consumer.start_handling)

	login_combos = get_credentials()

	sessions = []
	honeybees = []
	for b in clientbase.ClientBase.__subclasses__():
		bee = b(sessions)
		honeybees.append(bee)

	 	print 'Found ' + str(type(bee))

	#TODO: mail fetching at regular intervals,
	#      interactive sessions (ssh, telnet) at random intervals
	while True:
		for bee in honeybees:
			class_name = bee.__class__.__name__
			if class_name in login_combos:
				bee_info = login_combos[class_name]
				bee.do_session(bee_info['login'], bee_info['password'], 
					bee_info['server'], bee_info['port'])
		print sessions
		gevent.sleep(60)



def get_credentials():
	#TODO: Read from file or generate... Needs to be correlated with hive
	return {'pop3' : {'server' : '127.0.0.1', 'port' : 2100, 'login' : 'test', 'password' : 'test'}}

if __name__ == '__main__':
	main()