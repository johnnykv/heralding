import logging
import SimpleHTTPServer
import SocketServer
import base64

from handlerbase import HandlerBase
from BaseHTTPServer import BaseHTTPRequestHandler

class BeeHTTPHandler(BaseHTTPRequestHandler):

    def __init__(self, request, client_address, server, httpsession, options):

        # Had to call parent initializer later, because the methods used
        # in BaseHTTPRequestHandler.__init__() call handle_one_request()
        # which calls the do_* methods here. If _banner, _session and _options
        # are not set, we get a bunch of errors (Undefined reference blah blah)
        
        self._options = options
        if self._options.has_key('banner'):
            self._banner = self._options['banner']
        else:
            self._banner = "Microsoft-IIS/5.0"
        self._session = httpsession
        BaseHTTPRequestHandler.__init__(self, request, client_address, server)
        
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_AUTHHEAD(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm=\"Test\"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        if self.headers.getheader('Authorization') == None:
            self.do_AUTHHEAD()
            self.wfile.write('<html><b>Unauthorized</b></html>\r\n')
            pass

        # Test Username/password == test/test
        elif self.headers.getheader('Authorization') == 'Basic dGVzdDp0ZXN00':
            self.do_HEAD()
            self.wfile.write('<html><b>Authenticated!</b></html>\r\n')
            pass
        else:
            hdr = self.headers.getheader('Authorization')
            _, enc_uname_pwd = hdr.split(' ')
            dec_uname_pwd = base64.b64decode(enc_uname_pwd)
            uname, pwd = dec_uname_pwd.split(':')
            self._session.try_login(uname, pwd)
            self.do_AUTHHEAD()
            self.wfile.write('<html><b>Access Denied.</b></html>\r\n')
            pass

    def version_string(self):
        return self._banner

    #Disable logging provided by BaseHTTPServer
    def log_message(self, format, *args):
        pass

class http(HandlerBase):
    def __init__(self, sessions, options):
        super(http, self).__init__(sessions, options)
        self._options = options

    def handle_session(self, gsocket, address):
        session = self.create_session(address, gsocket)
        handler = BeeHTTPHandler(gsocket, address, None, httpsession = session,
                                    options = self._options)
