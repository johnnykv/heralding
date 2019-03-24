#!/usr/bin/python
# -*- coding: utf8 -*-

import asyncio
import collections
import logging

from .connection import Connection
from .prometheus import (
    CLIENT_SEND_BUFFER_FILL,
    RECEIVE_PUBLISH_COUNT,
    RECEIVE_PUBLISH_SIZE,
    SUBSCRIPTIONS,
    start_metrics_server,
)

log = logging.getLogger("hpfeeds.broker")


class Server(object):

    def __init__(self, auth, bind=None, exporter=None, sock=None, ssl=None, name='hpfeeds'):
        self.auth = auth
        self.name = name

        self.host, self.port = self._parse_endpoint(bind)
        self.sock = sock
        self.ssl = ssl

        self.exporter = self._parse_endpoint(exporter)

        self.connections = set()
        self.subscriptions = collections.defaultdict(list)

        self.when_started = asyncio.Future()

    def _parse_endpoint(self, endpoint):
        if not endpoint:
            return (None, None)
        elif ':' not in endpoint:
            raise ValueError('Invalid bind addr')
        else:
            return endpoint.split(':', 1)

    def get_authkey(self, identifier):
        return self.auth.get_authkey(identifier)

    def publish(self, source, chan, data):
        '''
        Called by a connection to push data to all subscribers of a channel
        '''
        RECEIVE_PUBLISH_COUNT.labels(source.ak, chan).inc()
        RECEIVE_PUBLISH_SIZE.labels(source.ak, chan).observe(len(data))

        for dest in self.subscriptions[chan]:
            CLIENT_SEND_BUFFER_FILL.labels(dest.ak).inc(len(data))
            dest.publish(source.ak, chan, data)

    def subscribe(self, source, chan):
        '''
        Subscribe a connection to a channel
        '''
        SUBSCRIPTIONS.labels(source.ak, chan).inc()
        self.subscriptions[chan].append(source)
        source.active_subscriptions.add(chan)

    def unsubscribe(self, source, chan):
        '''
        Unsubscribe a connection from a channel
        '''
        if chan in source.active_subscriptions:
            source.active_subscriptions.remove(chan)
        if source in self.subscriptions[chan]:
            self.subscriptions[chan].remove(source)
        SUBSCRIPTIONS.labels(source.ak, chan).dec()

    async def serve_forever(self):
        ''' Start handling connections. Await on this to listen forever. '''

        if self.exporter:
            metrics_server = await start_metrics_server(*self.exporter)
            metrics_server.app.broker = self

        server = await asyncio.get_event_loop().create_server(
            lambda: Connection(self),
            host=self.host,
            port=self.port,
            sock=self.sock,
            ssl=self.ssl,
        )

        self.when_started.set_result(None)

        try:
            while True:
                await asyncio.sleep(10)
        except asyncio.CancelledError:
            server.close()

            # for future in asyncio.as_completed([c.close() for c in list(self.connections)]):
            #    try:
            #        await future
            #    except Exception as e:
            #        log.exception(e)

            log.debug(f'Waiting for {self} to wrap up')
            await server.wait_closed()

            if self.exporter:
                log.debug('Waiting for stats server to wrap up')
                await metrics_server.cleanup()
