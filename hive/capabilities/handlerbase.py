class HandlerBase(object):
    def __init__(self, sessions):
        pass

    def handle(self, socket, address):
        raise Exception('Do no call base class!')

    def get_port(self):
        raise Exception('Do no call base class!')
