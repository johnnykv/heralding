from gevent.ssl import SSLSocket
from datetime import datetime
from socket import *

class HiveSSLSocket(SSLSocket):
    """
    Provides timings to the socket class.
    """

    def __init__(self, *args, **kwargs):
        super(HiveSSLSocket, self).__init__(*args, **kwargs)
        self.last_activity = datetime.now()

    def recv(self, *args):
        self.last_activity = datetime.now()
        return super(HiveSSLSocket, self).recv(*args)

    def recvfrom(self, *args):
        self.last_activity = datetime.now()
        return super(HiveSSLSocket, self).recvfrom(*args)

    def recvfrom_into(self, *args):
        self.last_activity = datetime.now()
        return super(HiveSSLSocket, self).recvfrom_into(*args)

    def last_update(self):
        """
        Returns seconds since the last time the socket was asked to receive data.
        """
        return (datetime.now() - self.last_activity).seconds
