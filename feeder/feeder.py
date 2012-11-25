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
from gevent import Greenlet
import gevent
import gevent.monkey
gevent.monkey.patch_all()
from bees import clientbase
from bees import pop3
from consumer import consumer
import logging
import gevent
import urllib2

def main():
	logging.debug('Starting feeder.')

	#TODO: Get bool from config file
	fetch_own_ip = True
	
	if fetch_own_ip:
		my_ip = urllib2.urlopen('http://api-sth01.exip.org/?call=ip').read()
		logging.info('Fetched %s as my external ip.' % (my_ip))
	
	targets = get_targets()

	sessions = {}

	#greenlet to consume and maintain data in sessions list
	sessions_consumer = consumer.Consumer(sessions)
	gevent.spawn(sessions_consumer.start_handling)

	
	honeybees = []
	for b in clientbase.ClientBase.__subclasses__():
		bee = b(sessions)
		honeybees.append(bee)
		logging.debug('Adding %s as a honeybee' % (bee.__class__.__name__))
	 	
	#TODO: 1. pop3 and imap at regular intervals,
	#      2. everything else at random intervals
	while True:
		for bee in honeybees:
			class_name = bee.__class__.__name__
			if class_name in targets:
				bee_info = targets[class_name]
				gevent.spawn(bee.do_session, bee_info['login'], bee_info['password'], 
					bee_info['server'], bee_info['port'], my_ip)
		gevent.sleep(60)



def get_targets():
	#TODO: Read from file or generate... Needs to be correlated with hive
	return {'pop3' : 
					{'server' : '127.0.0.1',
					 'port' : 2100,
					 'timing' : 'regular',
					 'login' : 'test',
					 'password' : 'test'}
					 }

if __name__ == '__main__':
	format_string = '%(asctime)-15s (%(funcName)s) %(message)s'
	logging.basicConfig(level=logging.DEBUG, format=format_string)
	main()