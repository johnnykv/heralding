import logging
import os
import pkgutil
import sys
from gevent.server import StreamServer

sys.path.append("./capabilities")
from Telnet import Telnet

from base import HandlerBase

def main():

	capabilities = get_capabilities();

	print capabilities;

	for c in capabilities:
		cap_class = type(c, (Telnet,), {})
		cap = cap_class()
		server = StreamServer(('0.0.0.0', 6543), cap.handle)
		print "Starting " + str(type(cap))
		server.serve_forever()

def get_capabilities():
	capability_names = []
	for f in os.listdir("capabilities"):
		if f == "base.py" or not f.endswith(".py"):
			continue
		module = f.split(".", 1)[0]
		capability_names.append(module)
		__import__(module, globals(), locals(), [], -1)
	return capability_names;

if __name__ == "__main__":
	main()