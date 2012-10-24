class HandlerBase(object):
       
        def handle(self, socket, address):
        	raise Exception('Do no call base class!')

        def get_port(self):
        	raise Exception('Do no call base class!')