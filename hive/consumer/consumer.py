import gevent
import os

from loggers import loggerbase
from loggers import consolelogger

class Consumer:

	def __init__(self, sessions):
		print "instance created"
		self.sessions = sessions

	def start_handling(self):
		active_loggers = self.get_loggers()

		while True:
			print "Current sessions count: %i" % (len(self.sessions),)
			for session_id in self.sessions.keys():
				session = self.sessions[session_id]
				if not session['connected']:
					#TODO: need to log before removal
					for logger in active_loggers:
						logger.log(session)
					del self.sessions[session_id]
			gevent.sleep(5)

	def stop_handling(self):
		pass

	def get_loggers(self):
		loggers = []
		for l in loggerbase.LoggerBase.__subclasses__():
			logger = l()
			loggers.append(logger)
		return loggers