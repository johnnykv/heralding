#!/usr/bin/python3
# License: LGPL
# Thanks a lot to the author of original telnetsrvlib - Ian Epperson (https://github.com/ianepperson)!
# Original repository - https://github.com/ianepperson/telnetsrvlib
# Telnet handler concrete class using green threads

import gevent
import gevent.queue
import gevent.select

from heralding.telnetsrv.telnetsrvlib import TelnetHandlerBase


class TelnetHandler(TelnetHandlerBase):
    "A telnet server handler using Gevent"
    def __init__(self, request, client_address, server):
        # Create a green queue for input handling
        self.cookedq = gevent.queue.Queue()
        # Call the base class init method
        super().__init__(request, client_address, server)

    def setup(self):
        '''Called after instantiation'''
        super().setup()
        # Spawn a greenlet to handle socket input
        self.greenlet_ic = gevent.spawn(self.inputcooker)
        # Note that inputcooker exits on EOF
        
        # Sleep for 0.5 second to allow options negotiation
        gevent.sleep(0.5)
        
    def finish(self):
        '''Called as the session is ending'''
        TelnetHandlerBase.finish(self)
        # Ensure the greenlet is dead
        self.greenlet_ic.kill()


    # -- Green input handling functions --

    def getc(self, block=True):
        """Return one character from the input queue"""
        try:
            return self.cookedq.get(block)
        except gevent.queue.Empty:
            return b''

    def inputcooker_socket_ready(self):
        """Indicate that the socket is ready to be read"""
        return gevent.select.select([self.sock.fileno()], [], [], 0) != ([], [], [])

    def inputcooker_store_queue(self, char):
        """Put the cooked data in the input queue (no locking needed)"""
        if isinstance(char, list) or isinstance(char, tuple) \
                or isinstance(char, str) or isinstance(char, bytes):
            for v in char:
                self.cookedq.put(v)
        else:
            self.cookedq.put(char)
