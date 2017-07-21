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

# Aniket Panse <contact@aniketpanse.in> grants Johnny Vestergaard <jkv@unixcluster.dk>
# a perpetual, worldwide, non-exclusive, no-charge, royalty-free, irrevocable
# copyright license to reproduce, prepare derivative works of, publicly
# display, publicly perform, sublicense, relicense, and distribute [the] Contributions
# and such derivative works.


import base64
import logging

from heralding.capabilities.handlerbase import HandlerBase
from heralding.libs.http.aioserver import AsyncBaseHTTPRequestHandler

logger = logging.getLogger(__name__)


class HTTPHandler(AsyncBaseHTTPRequestHandler):
    def __init__(self, reader, writer, httpsession, options):
        self._options = options
        if 'banner' in self._options:
            self._banner = self._options['banner']
        else:
            self._banner = 'Microsoft-IIS/5.0'
        self._session = httpsession
        address = writer.get_extra_info('address')
        super().__init__(reader, writer, address)

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_AUTHHEAD(self):
        self.send_response(401)
        # TODO: Value for basic realm...
        self.send_header('WWW-Authenticate', 'Basic realm=\"\"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        if self.headers['Authorization'] is None:
            self.do_AUTHHEAD()
        else:
            hdr = self.headers['Authorization']
            _, enc_uname_pwd = hdr.split(' ')
            dec_uname_pwd = str(base64.b64decode(enc_uname_pwd), 'utf-8')
            uname, pwd = dec_uname_pwd.split(':')
            self._session.add_auth_attempt('plaintext', username=uname, password=pwd)
            self.do_AUTHHEAD()
            headers_bytes = bytes(self.headers['Authorization'], 'utf-8')
            self.wfile.write(headers_bytes)
            self.wfile.write(b'not authenticated')

    # Disable logging provided by BaseHTTPServer
    def log_message(self, format_, *args):
        pass


class Http(HandlerBase):
    def __init__(self, options, loop):
        super().__init__(options, loop)
        self._options = options

    async def execute_capability(self, reader, writer, session):
        http_cap = HTTPHandler(reader, writer, httpsession=session, options=self._options)
        await http_cap.run()
        session.end_session()
