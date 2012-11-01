from loggerbase import LoggerBase

class ConsoleLogger(LoggerBase):

	def log(self, session):
		print session