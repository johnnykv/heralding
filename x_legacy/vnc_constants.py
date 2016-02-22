"""
    This file defines the constants used in the RFB Protocol, which is
    used by VNC.
"""

RFB_VERSION = 'RFB 003.007\n'
SUPPORTED_AUTH_METHODS = '\x01\x02'
VNC_AUTH = '\x02'
NO_AUTH = '\x01'
AUTH_FAILED = '\x00\x00\x00\x01'
AUTH_SUCCESSFUL = '\x00\x00\x00\x00'