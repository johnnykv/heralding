import logging

import SimpleHTTPServer
import SocketServer

from handlerbase import HandlerBase
from BaseHTTPServer import BaseHTTPRequestHandler

class BeeHTTPHandler(BaseHTTPRequestHandler):

    #TODO: Configurable
    banner = "Microsoft-IIS/5.0"

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
        ''' Present frontpage with user authentication. '''
        if self.headers.getheader('Authorization') == None:
            self.do_AUTHHEAD()
            self.wfile.write('<html><b>Unauthorized</b></html>\r\n')
            pass
        
        elif self.headers.getheader('Authorization') == 'Basic dGVzdDp0ZXN0':
            self.do_HEAD()
            self.wfile.write('<html><b>Authenticated!</b></html>\r\n')
            pass
        else:
            self.do_AUTHHEAD()
            self.wfile.write('<html><b>Access Denied.</b></html>\r\n')
            pass

    #Disable logging provided by BaseHTTPServer
    def log_message(self, format, *args):
        pass

    def version_string(self):
        return self.banner

class http(HandlerBase):
    def __init__(self, sessions, options):
        super(http, self).__init__(sessions, options)
        self._options = options

    def handle_session(self, gsocket, address):
        session = self.create_session(address, gsocket)
        handler = BeeHTTPHandler(gsocket, address, None)
