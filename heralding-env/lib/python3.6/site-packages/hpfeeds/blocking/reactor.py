from __future__ import absolute_import

import errno
import logging
import select
import socket
import sys
import threading

from . import queue


class Reactor(object):

    '''
    This class handles IO multiplexing and connection failure handling.
    '''

    def __init__(self, protocol_class, connector):
        self.protocol_class = protocol_class
        self.connector = connector

        self.closing = False
        self.when_connected = threading.Event()

        self._outbox = queue.Queue()

    def write(self, data):
        self._outbox.put_nowait(data)

    def close(self):
        self.sock.close()

    def _connect(self):
        '''
        Establish a connection using ``self.connector`` and then set up
        internal state for that new connection.
        '''
        self.sock = self.connector()

        self.sock.setblocking(False)

        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if sys.platform.startswith('linux'):
            self.sock.setsockopt(socket.SOL_TCP, socket.TCP_KEEPIDLE, 10)
            self.sock.setsockopt(socket.SOL_TCP, socket.TCP_KEEPINTVL, 5)
            self.sock.setsockopt(socket.SOL_TCP, socket.TCP_KEEPCNT, 3)

        self._buffer = b''
        self._outbox = queue.Queue()

        self.protocol = self.protocol_class()
        self.protocol.transport = self
        self.protocol.connection_made()

        self.when_connected.set()

    def _select(self):
        '''
        Block (and don't consume CPU) until self.sock or self._outbox is ready
        for us
        '''
        logging.debug('_select')

        want_read = [self.sock]
        want_write = []

        if self._buffer:
            want_write.append(self.sock)
        else:
            want_read.append(self._outbox)

        r, w, x = select.select(want_read, want_write, [])

        if self.sock in r and not self._socket_read_ready():
            return

        if self._outbox in r and not self._outbox_read_ready():
            return

        if self.sock in w and not self._socket_write_ready():
            return

    def _socket_read_ready(self):
        logging.debug('_socket_ready_ready')
        try:
            data = self.sock.recv(1024)
        except socket.error as e:
            # Interupted by.. interupt, try again
            if e.args[0] == errno.EAGAIN:
                return True

            # Would block, so return and go back to sleep
            if e.args[0] == errno.EWOULDBLOCK:
                return True

            raise

        if not data:
            self._connection_lost('Read failed')
            return False

        self.protocol.data_received(data)
        return True

    def _outbox_read_ready(self):
        logging.debug('_outbox_read_ready')

        try:
            self._buffer += self._outbox.get_nowait()
        except socket.error as e:
            # Interupted by.. interupt, try again
            if e.args[0] == errno.EAGAIN:
                return True

            # Would block, so return and go back to sleep
            if e.args[0] == errno.EWOULDBLOCK:
                return True
        except queue.Empty:
            # Someone lied - there is no data really
            # Go to sleep and try again later
            return True

        # If we were blocked waiting for something to land in queue there is
        # good chance the write socket is ready. Try to send.
        self._socket_write_ready()

    def _socket_write_ready(self):
        logging.debug('_socket_write_ready')
        try:
            sent = self.sock.send(self._buffer)
        except socket.error as e:
            # Interupted by.. interupt, try again
            if e.args[0] == errno.EAGAIN:
                return True

            # Would block, so return and go back to sleep
            if e.args[0] == errno.EWOULDBLOCK:
                return True

            raise

        if sent == 0:
            self._connection_lost('Write failed')
            return False

        self._buffer = self._buffer[sent:]
        return True

    def _connection_lost(self, reason):
        self.protocol.connection_lost(reason)
        try:
            self.sock.close()
        except Exception:
            pass
        self.sock = None
        self.when_connected.clear()

    def run_forever(self):
        while not self.closing:
            self._connect()

            while not self.closing and self.sock:
                self._select()

    def stop(self):
        self.closing = True
        # if self.sock:
        #     self._connection_lost('Client session terminated')


class ThreadReactor(Reactor):

    def start(self):
        self._thread = threading.Thread(target=self.run_forever)
        self._thread.start()

    def stop(self):
        super(ThreadReactor, self).stop()
        self._thread.join()
