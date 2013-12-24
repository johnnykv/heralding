from socket import *
import sys
import traceback
import logging

from gevent.server import StreamServer
from gevent import core
from gevent.socket import EWOULDBLOCK

from beeswarm.hive.helpers.h_socket import HiveSocket
from beeswarm.hive.helpers.h_ssl_socket import HiveSSLSocket

logger = logging.getLogger(__name__)


class HiveStreamServer(StreamServer):
    def __init__(self, listener, handle=None, backlog=None, spawn='default', **ssl_args):
        super(HiveStreamServer, self).__init__(listener, handle, backlog, spawn, **ssl_args)
        if ssl_args:
            ssl_args.setdefault('server_side', True)
            self.wrap_socket = wrap_socket
            self.ssl_args = ssl_args

    def exception_logger(self, greenlet):

        logger.exception('Unhandled "{0}" exception caused a greenlet to crash: {1}'
        .format(greenlet.exception, greenlet))

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
                    spawn(self._handle, client_socket, address).link_exception(receiver=self.exception_logger)
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


def wrap_socket(*args, **kwargs):
    """Create a new :class:`SSLSocket` instance."""
    return HiveSSLSocket(*args, **kwargs)
