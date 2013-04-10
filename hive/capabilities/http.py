# Copyright (C) 2013 Aniket Panse <contact@aniketpanse.in>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import base64
from BaseHTTPServer import BaseHTTPRequestHandler

from handlerbase import HandlerBase


class BeeHTTPHandler(BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server, httpsession, options):

        # Had to call parent initializer later, because the methods used
        # in BaseHTTPRequestHandler.__init__() call handle_one_request()
        # which calls the do_* methods here. If _banner, _session and _options
        # are not set, we get a bunch of errors (Undefined reference blah blah)

        self._options = options
        if 'banner' in self._options:
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
        if self.headers.getheader('Authorization') is None:
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
        handler = BeeHTTPHandler(gsocket, address, None, httpsession=session,
                                 options=self._options)
