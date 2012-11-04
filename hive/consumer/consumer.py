import gevent
import os

from loggers import loggerbase
from loggers import consolelogger
from loggers import sqlitelogger

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
					for logger in active_loggers:
						print "logging to " + str(logger)
						logger.log(session)
					del self.sessions[session_id]
			gevent.sleep(5)

	def stop_handling(self):
		pass

	def get_loggers(self):
		loggers = []
		for l in loggerbase.LoggerBase.__subclasses__():
			print l
			logger = l()
			loggers.append(logger)
		return loggers