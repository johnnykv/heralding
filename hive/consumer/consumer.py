import gevent
import os
import sys

sys.path.append('./consumer/loggers') #TODO: fix this!
from loggerbase import LoggerBase

class Consumer:

	def __init__(self, sessions):
		print "instance created"
		self.sessions = sessions

	def start_handling(self):
		loggers = self.get_loggers()

		while True:
			print "Current sessions count: %i" % (len(self.sessions),)
			for session_id in self.sessions.keys():
				session = self.sessions[session_id]
				if not session['connected']:
					#TODO: need to log before removal
					for logger in loggers:
						logger.log(session)
					del self.sessions[session_id]
			gevent.sleep(5)

	def stop_handling(self):
		pass

	def import_loggers(self):
		for f in os.listdir('./consumer/loggers'): #TODO: fix this!
			if f == 'loggerbase.py' or not f.endswith('.py'):
				continue
			module = f.split('.', 1)[0]
			__import__(module, globals(), locals(), [], -1)

	def get_loggers(self):
		self.import_loggers()
		
		loggers = []
		for l in LoggerBase.__subclasses__():
			logger = l()
			loggers.append(logger)
		return loggers