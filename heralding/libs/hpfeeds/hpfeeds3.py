# Copyright (C) 2010-2013 Mark Schloesser <ms@mwcollect.org
# This file is part of hpfeeds - https://github.com/rep/hpfeeds
# See the file 'LICENSE' for copying permission.

import sys
import struct
import socket
import hashlib
import logging
import time
import threading
import ssl

logger = logging.getLogger('pyhpfeeds')

OP_ERROR	= 0
OP_INFO		= 1
OP_AUTH		= 2
OP_PUBLISH	= 3
OP_SUBSCRIBE	= 4
BUFSIZ = 16384

__all__ = ["new", "FeedException"]

def msghdr(op, data):
	return struct.pack('!iB', 5+len(data), op) + data
def msgpublish(ident, chan, data):
#	if isinstance(data, str):
#		data = data.encode('latin1')
	return msghdr(OP_PUBLISH, struct.pack('!B', len(ident)) + ident + struct.pack('!B', len(chan)) + chan + data)
def msgsubscribe(ident, chan):
	return msghdr(OP_SUBSCRIBE, struct.pack('!B', len(ident)) + ident + chan)
def msgauth(rand, ident, secret):
	hash = hashlib.sha1(rand+secret).digest()
	return msghdr(OP_AUTH, struct.pack('!B', len(ident)) + ident + hash)

class FeedUnpack(object):
	def __init__(self):
		self.buf = bytearray()
	def __iter__(self):
		return self
	def __next__(self):
		return self.unpack()
	def feed(self, data):
		self.buf.extend(data)
	def unpack(self):
		if len(self.buf) < 5:
			raise StopIteration('No message.')

		ml, opcode = struct.unpack('!iB', buffer(self.buf,0,5))
		if len(self.buf) < ml:
			raise StopIteration('No message.')

		data = bytearray(buffer(self.buf, 5, ml-5))
		del self.buf[:ml]
		return opcode, data

class FeedException(Exception):
	pass
class Disconnect(Exception):
	pass

class HPC(object):
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
		self.unpacker = FeedUnpack()

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

		if not d: raise Disconnect()
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
			if not self.connected:
				while True:
					try:
						self.connect()
						break
					except socket.error as e:
						logger.warn('Socket error while connecting: {0}'.format(e))
						time.sleep(self.sleepwait)
					except FeedException as e:
						logger.warn('FeedException while connecting: {0}'.format(e))
						time.sleep(self.sleepwait)
					except Disconnect as e:
						logger.warn('Disconnect while connecting.')
						time.sleep(self.sleepwait)

	def connect(self):
		self.close_old()

		logger.info('connecting to {0}:{1}'.format(self.host, self.port))

		# Try other resolved addresses (IPv4 or IPv6) if failed.
		ainfos = socket.getaddrinfo(self.host, 1, socket.AF_UNSPEC, socket.SOCK_STREAM)
		for ainfo in ainfos:
			addr_family = ainfo[0]
			addr = ainfo[4][0]
			try:
				self.s = self.makesocket(addr_family)
				self.s.settimeout(self.timeout)
				self.s.connect((addr, self.port))
			except:
				import traceback
				traceback.print_exc()
				#print 'Could not connect to broker. %s[%s]' % (self.host, addr)
				continue
			else:
				self.connected = True
				break

		if self.connected == False:
			raise FeedException('Could not connect to broker [%s].' % (self.host))

		try: d = self.s.recv(BUFSIZ)
		except socket.timeout: raise FeedException('Connection receive timeout.')

		self.unpacker.feed(d)
		for opcode, data in self.unpacker:
			if opcode == OP_INFO:
				rest = buffer(data, 0)
				name, rest = rest[1:1+ord(rest[0])], buffer(rest, 1+ord(rest[0]))
				rand = str(rest)

				logger.debug('info message name: {0}, rand: {1}'.format(name, repr(rand)))
				self.brokername = name

				self.send(msgauth(rand, self.ident, self.secret))
				break
			else:
				raise FeedException('Expected info message at this point.')

		self.s.settimeout(None)
		self.s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

		if sys.platform in ('linux2', ):
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
							rest = buffer(data, 0)
							ident, rest = rest[1:1+ord(rest[0])], buffer(rest, 1+ord(rest[0]))
							chan, content = rest[1:1+ord(rest[0])], buffer(rest, 1+ord(rest[0]))

							message_callback(str(ident), str(chan), content)
						elif opcode == OP_ERROR:
							error_callback(data)

				except Disconnect:
					self.connected = False
					logger.info('Disconnected from broker.')
					break

				# end run loops if stopped
				if self.stopped: break

			if not self.stopped and self.reconnect:
				# connect again if disconnected
				self.tryconnect()

		logger.info('Stopped, exiting run loop.')

	def wait(self, timeout=1):
		self.s.settimeout(timeout)

		try:
			d = self.recv()
			if not d: return None

			self.unpacker.feed(d)
			for opcode, data in self.unpacker:
				if opcode == OP_ERROR:
					return data
		except Disconnect:
			pass

		return None

	def close_old(self):
		if self.s:
			try: self.s.close()
			except: pass

	def subscribe(self, chaninfo):
		if type(chaninfo) == str:
			chaninfo = [chaninfo,]
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
				if not self.reconnect: raise
				break

	def publish(self, chaninfo, data):
		if type(chaninfo) == str:
			chaninfo = [chaninfo,]
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
		try: self.s.close()
		except: logger.debug('Socket exception when closing (ignored though).')


class HPC_SSL(HPC):
	def __init__(self, *args, **kwargs):
		self.certfile = kwargs.pop("certfile", None)
		HPC.__init__(self, *args, **kwargs)

	def makesocket(self, addr_family):
		s = socket.socket(addr_family, socket.SOCK_STREAM)
		return ssl.wrap_socket(s, ca_certs=self.certfile, ssl_version=3, cert_reqs=2)


def new(host=None, port=10000, ident=None, secret=None, timeout=3, reconnect=True, sleepwait=20, certfile=None):
	if certfile:
		return HPC_SSL(host, port, ident, secret, timeout, reconnect, certfile=certfile)
	return HPC(host, port, ident, secret, timeout, reconnect)