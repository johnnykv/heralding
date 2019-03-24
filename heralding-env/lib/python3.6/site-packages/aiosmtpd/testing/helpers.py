"""Testing helpers."""

import sys
import socket
import struct
import asyncio
import logging
import warnings

from contextlib import ExitStack
from unittest.mock import patch


def reset_connection(client):
    # Close the connection with a TCP RST instead of a TCP FIN.  client must
    # be a smtplib.SMTP instance.
    #
    # https://stackoverflow.com/a/6440364/1570972
    #
    # socket(7) SO_LINGER option.
    #
    # struct linger {
    #   int l_onoff;    /* linger active */
    #   int l_linger;   /* how many seconds to linger for */
    # };
    #
    # Is this correct for Windows/Cygwin and macOS?
    struct_format = 'hh' if sys.platform == 'win32' else 'ii'
    l_onoff = 1
    l_linger = 0
    client.sock.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_LINGER,
        struct.pack(struct_format, l_onoff, l_linger))
    client.close()


# For integration with flufl.testing.

def setup(testobj):
    testobj.globs['resources'] = ExitStack()


def teardown(testobj):
    testobj.globs['resources'].close()


def make_debug_loop():
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    return loop


def start(plugin):
    if plugin.stderr:
        # Turn on lots of debugging.
        patch('aiosmtpd.smtp.make_loop', make_debug_loop).start()
        logging.getLogger('asyncio').setLevel(logging.DEBUG)
        logging.getLogger('mail.log').setLevel(logging.DEBUG)
        warnings.filterwarnings('always', category=ResourceWarning)
