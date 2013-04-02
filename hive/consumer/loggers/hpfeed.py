import struct
import socket
import hashlib
import logging
import json
import uuid
import time
from gevent import Greenlet


from datetime import datetime
from ConfigParser import ConfigParser
from loggerbase import LoggerBase

logger = logging.getLogger(__name__)

"""
Based on Lukas Rists hpfeed implementation for glastopf
https://raw.github.com/glastopf/glastopf/master/modules/reporting/auxiliary/hp_feed.py
which in turn is based on Mark Schloessers HPFeed example cli client:
https://raw.github.com/rep/hpfeeds/master/cli/feed.py (9/25/11)
"""

OP_ERROR = 0
OP_INFO = 1
OP_AUTH = 2
OP_PUBLISH = 3


def msghdr(op, data):
    return struct.pack('!iB', 5 + len(data), op) + data


def msgpublish(ident, chan, data):
    if isinstance(data, str):
        data = data.encode('latin1')
    return msghdr(OP_PUBLISH, struct.pack('!B', len(ident)) + ident + struct.pack('!B', len(chan)) + chan + data)


def msgauth(rand, ident, secret):
    hash = hashlib.sha1(rand + secret).digest()
    return msghdr(OP_AUTH, struct.pack('!B', len(ident)) + ident + hash)


class FeedUnpack(object):
    def __init__(self):
        self.buf = bytearray()

    def __iter__(self):
        return self

    def next(self):
        return self.unpack()

    def feed(self, data):
        self.buf.extend(data)

    def unpack(self):
        if len(self.buf) < 5:
            raise StopIteration('No message.')

        ml, opcode = struct.unpack('!iB', buffer(self.buf, 0, 5))
        if len(self.buf) < ml:
            raise StopIteration('No message.')

        data = bytearray(buffer(self.buf, 5, ml - 5))
        del self.buf[:ml]
        return opcode, data


class HPFeed(LoggerBase):
    def __init__(self, config="hive.cfg"):
        conf_parser = ConfigParser()
        conf_parser.read(config)

        self.host = conf_parser.get("log_hpfeed", "host")
        self.port = conf_parser.getint("log_hpfeed", "port")
        self.secret = conf_parser.get("log_hpfeed", "secret").encode('latin1')
        self.chan = conf_parser.get("log_hpfeed", "chan").encode('latin1')
        self.ident = conf_parser.get("log_hpfeed", "ident").encode('latin1').strip()
        self.enabled = True

        Greenlet.spawn(self._start)

    def broker_read(self):
        self.unpacker = FeedUnpack()
        data = self.socket.recv(1024)
        while data:
            self.unpacker.feed(data)
            for opcode, data in self.unpacker:
                if opcode == OP_INFO:
                    rest = buffer(data, 0)
                    name, rest = rest[1:1 + ord(rest[0])], buffer(rest, 1 + ord(rest[0]))
                    rand = str(rest)
                    self.socket.send(msgauth(rand, self.ident, self.secret))
                elif opcode == OP_ERROR:
                    logger.error("Error from server: {0}".format(data))
            data = self.socket.recv(1024)

    def stop(self):
        self.enabled = False

    def _start(self):
        while self.enabled:
            try:
                logger.info("Connecting to feed broker at {0}:{1}".format(self.host, self.port))
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((self.host, self.port))
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            except Exception as ex:
                logger.warning('Could not connect to hpfeed broker: {0}'.format(ex))
                self.socket.close()
                time.sleep(5)
            else:
                logger.info("Connected to hpfeed broker.")
                try:
                    self.broker_read()
                except Exception as ex:
                    logger.warning('Connection lost to hpfeed broker: {0}'.format(ex))

        logger.info("HPFeeds logger stopped.")

    def log(self, session):
        data = json.dumps(session.to_dict(), default=self.json_default)
        try:
            self.socket.send(msgpublish(self.ident, self.chan, data))
        except Exception as e:
            logger.exception("Connection error: {0}".format(e))
            self._start()
            self.socket.send(msgpublish(self.ident, self.chan, data))

    def json_default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, uuid.UUID):
            return str(obj)
        else:
            return None
