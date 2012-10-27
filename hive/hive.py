import os
import sys
from gevent.server import StreamServer
from gevent import Greenlet
import gevent
import Consumer

sys.path.append('./capabilities')
from base import HandlerBase

def main():
	import_capabilities()
	servers = []
	sessions = {}

	#greenlet to consume and maintain data in sessions list
	sessions_consumer = Consumer.Consumer(sessions)
	Greenlet.spawn(sessions_consumer.start_handling)

	for c in HandlerBase.__subclasses__():
		cap = c(sessions)
		server = StreamServer(('0.0.0.0', cap.get_port()), cap.handle)
		servers.append(server)
		print 'Starting ' + str(type(cap))
		server.start()
	print 'all started'
	
	stop_events = []
	for s in servers:
		stop_events.append(s._stopped_event)

	gevent.joinall(stop_events)

def import_capabilities():
	for f in os.listdir('capabilities'):
		if f == 'base.py' or not f.endswith('.py'):
			continue
		module = f.split('.', 1)[0]
		#capability_names.append(module)
		__import__(module, globals(), locals(), [], -1)

if __name__ == '__main__':
	main()