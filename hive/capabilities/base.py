class HandlerBase(object):
       
        def handle(self, socket, address):
        	raise Exception("This is not supposed to happen")

        def get_port(self):
        	raise Exception("This is not supposed to happen")
        
