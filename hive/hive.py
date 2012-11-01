from gevent.server import StreamServer
from gevent import Greenlet
import gevent
from consumer import consumer
from capabilities import handlerbase
from capabilities import pop3

def main():
	servers = []
	sessions = {}

	#greenlet to consume and maintain data in sessions list
	sessions_consumer = consumer.Consumer(sessions)
	Greenlet.spawn(sessions_consumer.start_handling)

	#protocol handlers
	for c in handlerbase.HandlerBase.__subclasses__():
		print c
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

if __name__ == '__main__':
	main()