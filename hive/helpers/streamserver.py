from gevent.server import StreamServer
from hive.helpers.h_socket import HiveSocket
from gevent import core
from gevent.socket import EWOULDBLOCK
from socket import *

import sys
import traceback

class HiveStreamServer(StreamServer):
    def __init__(self, listener, handle=None, backlog=None, spawn='default', **ssl_args):
        super(HiveStreamServer, self).__init__(listener, handle, backlog, spawn, **ssl_args)

    #only difference from gevent.server.py is that socket is replaced by HiveSocket.
    def _do_accept(self, event, _evtype):
        assert event is self._accept_event
        for _ in xrange(self.max_accept):
            address = None
            try:
                if self.full():
                    self.stop_accepting()
                    return
                try:
                    client_socket, address = self.socket.accept()
                except error, err:
                    if err[0] == EWOULDBLOCK:
                        return
                    raise
                self.delay = self.min_delay
                client_socket = HiveSocket(_sock=client_socket)
                spawn = self._spawn
                if spawn is None:
                    self._handle(client_socket, address)
                else:
                    spawn(self._handle, client_socket, address)
            except:
                traceback.print_exc()
                ex = sys.exc_info()[1]
                if self.is_fatal_error(ex):
                    self.kill()
                    sys.stderr.write('ERROR: %s failed with %s\n' % (self, str(ex) or repr(ex)))
                    return
                try:
                    if address is None:
                        sys.stderr.write('%s: Failed.\n' % (self, ))
                    else:
                        sys.stderr.write('%s: Failed to handle request from %s\n' % (self, address, ))
                except Exception:
                    traceback.print_exc()
                if self.delay >= 0:
                    self.stop_accepting()
                    self._start_accepting_timer = core.timer(self.delay, self.start_accepting)
                    self.delay = min(self.max_delay, self.delay * 2)
                return