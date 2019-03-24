from __future__ import absolute_import

import logging
import socket
import sys

from hpfeeds.protocol import msgpublish, msgsubscribe, msgunsubscribe

from .protocol import ClientProtocol
from .queue import Queue
from .reactor import ThreadReactor


class Protocol(ClientProtocol):

    def __init__(self, session):
        self.session = session
        super(Protocol, self).__init__(session.ident, session.secret)

    def on_publish(self, ident, channel, payload):
        self.session.read_queue.put_nowait((ident, channel, payload))


class ClientSession(object):

    '''
    Create and maintain a session with the hpfeeds broker.

    The connection is managed in a dedicated thread.
    '''

    def __init__(self, host, port, ident, secret):
        self.host = host
        self.port = port
        self.ident = ident
        self.secret = secret
        self.subscriptions = set()

        self.read_queue = Queue()

        self._reactor = ThreadReactor(self._build_protocol, self._connect)

    def _build_protocol(self):
        return Protocol(self)

    def _connect(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, self.port))
        except Exception as e:
            logging.exception(e)
            return None
        return sock

    def start(self):
        self._reactor.start()

    def stop(self):
        self._reactor.stop()

    def publish(self, channel, payload):
        self._reactor.write(msgpublish(self.ident, channel, payload))

    def publish_iter(self, channel, iterator):
        for payload in iterator:
            self.publish(channel, payload)

    def subscribe(self, channel):
        self.subscriptions.add(channel)
        self._reactor.write(msgsubscribe(self.ident, channel))

    def unsubscribe(self, channel):
        self.subscriptions.discard(channel)
        self._reactor.write(msgunsubscribe(self.ident, channel))

    def read(self):
        return self.read_queue.get()

    def __enter__(self):
        self.start()
        self._reactor.when_connected.wait()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def __iter__(self):
        return self

    def __next__(self):
        if self._reactor.closing:
            raise StopIteration()
        return self.read()

    if sys.version_info[0] == 2:
        def next(self):
            return self.__next__()
