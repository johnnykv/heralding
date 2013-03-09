import gevent.socket
from datetime import datetime
from socket import *

class HiveSocket(gevent.socket.socket):
    """
    Provides timings to the socket class.
    """

    def __init__(self, family=AF_INET, type=SOCK_STREAM, proto=0, _sock=None):
        super(HiveSocket, self).__init__(family, type, proto, _sock)
        self.last_activity = datetime.now()

    def recv(self, *args):
        self.last_activity = datetime.now()
        return super(HiveSocket, self).recv(*args)

    def recvfrom(self, *args):
        self.last_activity = datetime.now()
        return super(HiveSocket, self).recvfrom(*args)

    def recvfrom_into(self, *args):
        self.last_activity = datetime.now()
        return super(HiveSocket, self).recvfrom_into(*args)

    def last_update(self):
        """
        Returns seconds since the last time the socket was asked to receive data.
        """
        return (datetime.now() - self.last_activity).seconds
