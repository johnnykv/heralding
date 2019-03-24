# Copyright (C) 2010-2013 Mark Schloesser <ms@mwcollect.org
# This file is part of hpfeeds - https://github.com/rep/hpfeeds
# See the file 'LICENSE' for copying permission.

import logging
import socket
import ssl
import sys
import threading
import time

from .exceptions import Disconnect, FeedException
from .protocol import (
    BUFSIZ,
    OP_ERROR,
    OP_INFO,
    OP_PUBLISH,
    Unpacker,
    msgauth,
    msgpublish,
    msgsubscribe,
    readerror,
    readinfo,
    readpublish,
)

logger = logging.getLogger('pyhpfeeds')


__all__ = ["new", "FeedException"]


class Client(object):

    def __init__(self, host, port, ident, secret, timeout=3, reconnect=True, sleepwait=20):
        self.host, self.port = host, port
        self.ident, self.secret = ident, secret
        self.timeout = timeout
        self.reconnect = reconnect
        self.sleepwait = sleepwait
        self.brokername = 'unknown'
        self.connected = False
        self.stopped = False
        self.s = None
        self.connecting_lock = threading.Lock()
        self.subscriptions = set()
        self.unpacker = Unpacker()

        self.tryconnect()

    def makesocket(self, addr_family):
        return socket.socket(addr_family, socket.SOCK_STREAM)

    def recv(self):
        try:
            d = self.s.recv(BUFSIZ)
        except socket.timeout:
            return ""
        except socket.error as e:
            logger.warn("Socket error: %s", e)
            raise Disconnect()

        if not d:
            logger.warn("recv() returned empty string")
            raise Disconnect()

        return d

    def send(self, data):
        try:
            self.s.sendall(data)
        except socket.timeout:
            logger.warn("Timeout while sending - disconnect.")
            raise Disconnect()
        except socket.error as e:
            logger.warn("Socket error: %s", e)
            raise Disconnect()

        return True

    def tryconnect(self):
        with self.connecting_lock:
            if self.connected:
                return

            while True:
                try:
                    return self.connect()
                except socket.error as e:
                    logger.warn(
                        'Socket error while connecting',
                        exc_info=e,
                    )
                except FeedException as e:
                    logger.warn(
                        'FeedException while connecting',
                        exc_info=e,
                    )
                except Disconnect as e:
                    logger.warn('Disconnect while connecting.')

                time.sleep(self.sleepwait)

    def connect(self):
        self.close_old()

        logger.info('connecting to {0}:{1}'.format(self.host, self.port))

        # Try other resolved addresses (IPv4 or IPv6) if failed.
        ainfos = socket.getaddrinfo(
            self.host,
            1,
            socket.AF_UNSPEC,
            socket.SOCK_STREAM,
        )

        for ainfo in ainfos:
            addr_family = ainfo[0]
            addr = ainfo[4][0]
            try:
                self.s = self.makesocket(addr_family)
                self.s.settimeout(self.timeout)
                self.s.connect((addr, self.port))
            except Exception:
                logger.exception('Could not connect to broker {}[{}]'.format(
                    self.host,
                    addr,
                ))
                continue
            else:
                self.connected = True
                break

        if self.connected is False:
            raise FeedException(
                'Could not connect to broker {}'.format(self.host)
            )

        self.unpacker.reset()

        try:
            d = self.s.recv(BUFSIZ)
        except socket.timeout:
            raise FeedException('Connection receive timeout.')

        self.unpacker.feed(d)
        for opcode, data in self.unpacker:
            if opcode == OP_INFO:
                name, rand = readinfo(data)
                logger.debug(
                    'info message name: {0}, rand: {1!r}'.format(name, rand)
                )
                self.brokername = name

                self.send(msgauth(rand, self.ident, self.secret))
                break
            else:
                raise FeedException('Expected OP_INFO but got another opcode.')
        else:
            raise FeedException('Expected OP_INFO but cannot assemble complete message')

        self.s.settimeout(None)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if sys.platform.startswith('linux'):
            self.s.setsockopt(socket.SOL_TCP, socket.TCP_KEEPIDLE, 10)

    def run(self, message_callback, error_callback):
        while not self.stopped:
            self._subscribe()
            while self.connected:
                try:
                    d = self.recv()
                    self.unpacker.feed(d)

                    for opcode, data in self.unpacker:
                        if opcode == OP_PUBLISH:
                            message_callback(*readpublish(data))
                        elif opcode == OP_ERROR:
                            error_callback(readerror(data))

                except Disconnect as e:
                    self.connected = False
                    logger.info('Disconnected from broker.', exc_info=e)
                    break

                # end run loops if stopped
                if self.stopped:
                    break

            if not self.stopped and self.reconnect:
                # connect again if disconnected
                self.tryconnect()

        logger.info('Stopped, exiting run loop.')

    def _read_message(self):
        d = self.recv()
        if not d:
            raise Disconnect()

        self.unpacker.feed(d)
        for opcode, data in self.unpacker:
            return (opcode, data)

    def wait(self, timeout=1):
        self.s.settimeout(timeout)

        try:
            d = self.recv()
            if not d:
                return None

            self.unpacker.feed(d)
            for opcode, data in self.unpacker:
                if opcode == OP_ERROR:
                    return readerror(data)
        except Disconnect:
            pass

        return None

    def close_old(self):
        if self.s:
            try:
                self.s.close()
            except Exception:
                pass

    def subscribe(self, chaninfo):
        if type(chaninfo) == str:
            chaninfo = [chaninfo]
        for c in chaninfo:
            self.subscriptions.add(c)

    def _subscribe(self):
        for c in self.subscriptions:
            try:
                logger.debug('Sending subscription for {0}.'.format(c))
                self.send(msgsubscribe(self.ident, c))
            except Disconnect:
                self.connected = False
                logger.info('Disconnected from broker (in subscribe).')
                if not self.reconnect:
                    raise
                break

    def publish(self, chaninfo, data):
        if type(chaninfo) == str:
            chaninfo = [chaninfo]
        for c in chaninfo:
            try:
                self.send(msgpublish(self.ident, c, data))
            except Disconnect:
                self.connected = False
                logger.info('Disconnected from broker (in publish).')
                if self.reconnect:
                    self.tryconnect()
                else:
                    raise

    def stop(self):
        self.stopped = True

    def close(self):
        try:
            self.s.close()
        except Exception:
            logger.debug('Socket exception when closing (ignored though).')


class SslClient(Client):
    def __init__(self, *args, **kwargs):
        self.certfile = kwargs.pop("certfile", None)
        super(SslClient, self).__init__(*args, **kwargs)

    def makesocket(self, addr_family):
        sock = socket.socket(addr_family, socket.SOCK_STREAM)
        return ssl.wrap_socket(
            sock,
            ca_certs=self.certfile,
            ssl_version=3,
            cert_reqs=2,
        )


def new(host=None, port=10000, ident=None, secret=None, timeout=3, reconnect=True, sleepwait=20, certfile=None):
    if certfile:
        return SslClient(host, port, ident, secret, timeout, reconnect, certfile=certfile)
    return Client(host, port, ident, secret, timeout, reconnect)
