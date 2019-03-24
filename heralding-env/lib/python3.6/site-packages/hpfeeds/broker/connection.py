#!/usr/bin/python
# -*- coding: utf8 -*-

import asyncio
import logging
import os
import socket
import sys

import wrapt

from hpfeeds.asyncio.protocol import BaseProtocol
from hpfeeds.protocol import OP_AUTH, OP_PUBLISH, SIZES, hashsecret

from .prometheus import (
    CLIENT_CONNECTIONS,
    CLIENT_RECEIVE_BUFFER_FILL,
    CLIENT_SEND_BUFFER_DEADLINE_RECOVER,
    CLIENT_SEND_BUFFER_DEADLINE_START,
    CLIENT_SEND_BUFFER_DRAIN,
    CONNECTION_ERROR,
    CONNECTION_LOST,
    CONNECTION_MADE,
    CONNECTION_READY,
)

log = logging.getLogger('hpfeeds.broker.connection')


class MeteredSocket(wrapt.ObjectProxy):

    def __init__(self, sock, ak):
        super().__init__(sock)
        self._self_ak = ak

    def send(self, buffer):
        n = self.__wrapped__.send(buffer)
        CLIENT_SEND_BUFFER_DRAIN.labels(self._self_ak).inc(n)
        return n


class MeteredSSLObject(wrapt.ObjectProxy):

    def __init__(self, sock, ak):
        super().__init__(sock)
        self._self_ak = ak

    def write(self, buffer):
        n = self.__wrapped__.write(buffer)
        CLIENT_SEND_BUFFER_DRAIN.labels(self._self_ak).inc(n)
        return n


class Connection(BaseProtocol):

    def __init__(self, server):
        self.server = server

        self.uid = None
        self.ak = None
        self.pubchans = []
        self.subchans = []

        self.active_subscriptions = set()

        self.authrand = os.urandom(4)

        self._deadline_timer = None

        super().__init__()

    def pause_writing(self):
        async def deadline_timer():
            await asyncio.sleep(60)
            CONNECTION_ERROR.labels(self.ak, 'deadline-timer-expired').inc()
            self.error("Backpressure deadline timer expired")
            self.transport.close()

        CLIENT_SEND_BUFFER_DEADLINE_START.labels(self.ak).inc()
        self._deadline_timer = asyncio.ensure_future(deadline_timer())

    def resume_writing(self):
        if self._deadline_timer:
            CLIENT_SEND_BUFFER_DEADLINE_RECOVER.labels(self.ak).inc()
            self._deadline_timer.cancel()
            self._deadline_timer = None

    def connection_made(self, transport):
        CLIENT_CONNECTIONS.inc()
        CONNECTION_MADE.inc()

        self.server.connections.add(self)

        self.transport = transport
        self.peer, self.port = transport.get_extra_info('peername')

        sock = transport.get_extra_info('socket')
        if sock is not None:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            if sys.platform.startswith('linux'):
                sock.setsockopt(socket.SOL_TCP, socket.TCP_KEEPIDLE, 10)
                sock.setsockopt(socket.SOL_TCP, socket.TCP_KEEPINTVL, 5)
                sock.setsockopt(socket.SOL_TCP, socket.TCP_KEEPCNT, 3)

        self.info(self.server.name, self.authrand)

        log.debug(f'{self}: Sent auth challenge')

    def connection_lost(self, reason):
        CLIENT_CONNECTIONS.dec()
        CONNECTION_LOST.labels(self.ak).inc()

        for chan in list(self.active_subscriptions):
            self.server.unsubscribe(self, chan)

        self.server.connections.discard(self)
        self.server = None

        log.debug(f'Disconnection from {self}; cleanup completed.')

    def __str__(self):
        peer, port = self.peer, self.port
        ident = self.ak
        owner = self.uid
        return (
            f'<Connection ident={ident} owner={owner} peer={peer} port={port}'
        )

    def data_received(self, data):
        if self.ak:
            CLIENT_RECEIVE_BUFFER_FILL.labels(self.ak).inc(len(data))
        return super().data_received(data)

    def message_received(self, opcode, message):
        if not self.uid and opcode != OP_AUTH:
            CONNECTION_ERROR.labels('', 'invalid-first-message').inc()
            self.error("First message was not AUTH")
            self.transport.close()
            return

        return super().message_received(opcode, message)

    def on_auth(self, ident, secret):
        akrow = self.server.get_authkey(ident)
        if not akrow:
            CONNECTION_ERROR.labels(ident, 'invalid-ident').inc()
            self.error(f"Authentication failed for {ident}")
            self.transport.close()
            return

        akhash = hashsecret(self.authrand, akrow["secret"])
        if not akhash == secret:
            CONNECTION_ERROR.labels(ident, 'invalid-secret').inc()
            self.error(f"Authentication failed for {ident}")
            self.transport.close()
            return

        self.ak = ident
        self.uid = akrow["owner"]
        self.pubchans = akrow.get("pubchans", [])
        self.subchans = akrow.get("subchans", [])

        if hasattr(self.transport, '_sock'):
            self.transport._sock = MeteredSocket(self.transport._sock, self.ak)
        elif hasattr(self.transport, '_ssl_protocol'):
            self.transport._ssl_protocol._sslpipe._sslobj = MeteredSSLObject(self.transport._ssl_protocol._sslpipe._sslobj, self.ak)

        high = SIZES[OP_PUBLISH] * 50
        self.transport.set_write_buffer_limits(high=high)

        CONNECTION_READY.labels(ident).inc()

    def on_publish(self, ident, chan, payload):
        if not ident == self.ak:
            CONNECTION_ERROR.labels(ident, 'ident-mismatch-pub').inc()
            self.error(f"Invalid authkey in message, ident={ident}")
            self.transport.close()
            return

        if chan not in self.pubchans:
            CONNECTION_ERROR.labels(ident, 'no-pub-permission').inc()
            self.error(f'Authkey not allowed to pub here. ident={ident}, chan={chan}')
            self.transport.close()
            return

        self.server.publish(self, chan, payload)

    def on_subscribe(self, ident, chan):
        if chan not in self.subchans:
            CONNECTION_ERROR.labels(ident, 'no-sub-permission').inc()
            self.error(f'Authkey not allowed to sub here. ident={self.ak}, chan={chan}')
            self.transport.close()
        self.server.subscribe(self, chan)

    def on_unsubscribe(self, ident, chan):
        self.server.unsubscribe(self, chan)
