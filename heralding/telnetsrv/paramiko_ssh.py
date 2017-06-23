# License: LGPL
# Thanks a lot to the author of original telnetsrvlib - Ian Epperson (https://github.com/ianepperson)!
# Original repository - https://github.com/ianepperson/telnetsrvlib

import logging
from threading import Thread
from socketserver import BaseRequestHandler

from paramiko import Transport, ServerInterface, AUTH_SUCCESSFUL, AUTH_FAILED,\
                     OPEN_SUCCEEDED, OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

log = logging.getLogger(__name__)


class TelnetToPtyHandler:
    """Mixin to turn TelnetHandler into PtyHandler"""
    def __init__(self, *args):
        super().__init__(*args)

    # Don't mention these, client isn't listening for them.  Blank the dicts.
    DOACK = {}
    WILLACK = {}

    # Do not ask for auth in the PTY, it'll be handled via SSH, then passed in with the request
    def authentication_ok(self):
        """Checks the authentication and sets the username of the currently connected terminal.  Returns True or False"""
        # Since authentication already happened, this should always return true
        self.username = self.request.username
        return True


class SSHHandler(ServerInterface, BaseRequestHandler):
    telnet_handler = None
    pty_handler = None
    host_key = None
    username = None

    def __init__(self, request, client_address, server):
        self.request = request
        self.client_address = client_address
        self.tcp_server = server

        # Keep track of channel information from the transport
        self.channels = {}

        self.client = request._sock
        # Transport turns the socket into an SSH transport
        self.transport = Transport(self.client)

        # Create the PTY handler class by mixing in
        TelnetHandlerClass = self.telnet_handler

        class MixedPtyHandler(TelnetToPtyHandler, TelnetHandlerClass):
            def __init__(self, *args):
                TelnetHandlerClass.__init__(self, *args)

        self.pty_handler = MixedPtyHandler

        # Call the base class to run the handler
        BaseRequestHandler.__init__(self, request, client_address, server)

    def setup(self):
        """Setup the connection."""
        raise NotImplementedError("Please Implement the setup method")

    class dummy_request:
        def __init__(self):
            self._sock = None

    @classmethod
    def streamserver_handle(cls, socket, address):
        """Translate this class for use in a StreamServer"""
        request = cls.dummy_request()
        request._sock = socket
        server = None
        cls(request, address, server)

    def finish(self):
        """Called when the socket closes from the client."""
        self.transport.close()

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return OPEN_SUCCEEDED
        return OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def set_username(self, username):
        self.username = username
        log.info('User logged in: %s' % username)

    # Handle User Authentication ######

    # Override these with functions to use for callbacks
    authCallback = None
    authCallbackKey = None
    authCallbackUsername = None

    def get_allowed_auths(self, username):
        methods = []
        if self.authCallbackUsername is not None:
            methods.append('none')
        if self.authCallback is not None:
            methods.append('password')
        if self.authCallbackKey is not None:
            methods.append('publickey')

        if not methods:
            # If no methods were defined, use none
            methods.append('none')

        log.debug('Configured authentication methods: %r', methods)
        return ','.join(methods)

    def check_auth_password(self, username, password):
        # print 'check_auth_password(%s, %s)' % (username, password)
        try:
            self.authCallback(username, password)
        except:
            return AUTH_FAILED
        else:
            self.set_username(username)
            return AUTH_SUCCESSFUL

    def check_auth_publickey(self, username, key):
        # print 'Auth attempt with key: ' + hexlify(key.get_fingerprint())
        try:
            self.authCallbackKey(username, key)
        except:
            return AUTH_FAILED
        else:
            self.set_username(username)
            return AUTH_SUCCESSFUL
            # if (username == 'xx') and (key == self.good_pub_key):
            #    return AUTH_SUCCESSFUL

    def check_auth_none(self, username):
        if self.authCallbackUsername is None:
            self.set_username(username)
            return AUTH_SUCCESSFUL
        try:
            self.authCallbackUsername(username)
        except:
            return AUTH_FAILED
        else:
            self.set_username(username)
            return AUTH_SUCCESSFUL

    def check_channel_shell_request(self, channel):
        """Request to start a shell on the given channel"""
        try:
            self.channels[channel].start()
        except KeyError:
            log.error('Requested to start a channel (%r) that was not previously set up.', channel)
            return False
        else:
            return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth,
                                  pixelheight, modes):
        """Request to allocate a PTY terminal."""
        # self.sshterm = term
        # print "term: %r, modes: %r" % (term, modes)
        log.debug('PTY requested.  Setting up %r.', self.telnet_handler)
        pty_thread = Thread(target=self.start_pty_request, args=(channel, term, modes))
        self.channels[channel] = pty_thread

        return True

    def start_pty_request(self, channel, term, modes):
        """Start a PTY - intended to run it a (green)thread."""
        request = self.dummy_request()
        request._sock = channel
        request.modes = modes
        request.term = term
        request.username = self.username

        # modes = http://www.ietf.org/rfc/rfc4254.txt page 18
        # for i in xrange(50):
        #    print "%r: %r" % (int(m[i*5].encode('hex'), 16), int(''.join(m[i*5+1:i*5+5]).encode('hex'), 16))


        # This should block until the user quits the pty
        self.pty_handler(request, self.client_address, self.tcp_server)

        # Shutdown the entire session
        self.transport.close()
