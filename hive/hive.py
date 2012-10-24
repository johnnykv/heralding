import os
import sys
from gevent.server import StreamServer
import gevent

sys.path.append('./capabilities')
from pop3 import pop3

def main():

	capabilities = get_capabilities();

	print capabilities;

	servers = []
	for c in capabilities:
		cap_class = type(c, (pop3,), {})
		cap = cap_class()
		server = StreamServer(('0.0.0.0', cap.get_port()), cap.handle)
		servers.append(server)
		print 'Starting ' + str(type(cap))
		server.start()
	print 'all started'
	
	stop_events = []
	for s in servers:
		stop_events.append(s._stopped_event)

	gevent.joinall(stop_events)

def get_capabilities():
	capability_names = []
	for f in os.listdir('capabilities'):
		if f == 'base.py' or not f.endswith('.py'):
			continue
		module = f.split('.', 1)[0]
		capability_names.append(module)
		__import__(module, globals(), locals(), [], -1)
	return capability_names;

if __name__ == '__main__':
	main()