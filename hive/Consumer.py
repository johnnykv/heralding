import gevent

class Consumer:

	def __init__(self, sessions):
		print "instanc created"
		self.sessions = sessions

	def start_handling(self):
		while True:
			print "Current sessions count: %i" % (len(self.sessions),)
			for session_id in self.sessions.keys():
				session = self.sessions[session_id]
				if not session['connected']:
					#TODO: need to log before removal
					del self.sessions[session_id]
			gevent.sleep(5)

	def stop_handling(self):
		pass