from __future__ import absolute_import

import os
import socket

try:
    import queue
except ImportError:
    import Queue as queue

__all__ = [
    'Empty',
    'Queue',
]


Empty = queue.Queue


class Queue(queue.Queue, object):

    def __init__(self):
        super(Queue, self).__init__()
        if os.name == 'posix':
            self._putsocket, self._getsocket = socket.socketpair()
        else:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind(('127.0.0.1', 0))
            server.listen(1)
            self._putsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._putsocket.connect(server.getsockname())
            self._getsocket, _ = server.accept()
            server.close()

    def fileno(self):
        return self._getsocket.fileno()

    def put(self, item, block=True):
        super(Queue, self).put(item, block)
        self._putsocket.send(b'x')

    def get(self, block=True):
        self._getsocket.recv(1)
        return super(Queue, self).get(block)
