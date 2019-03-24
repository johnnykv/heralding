# We need this in order to reduce the number of third-party modules.
# The main idea is to replace rfile/wfile with reader/writer and to
# add async/await syntax. So, it is http.server.BaseHTTPRequestHandler
# code, but adjusted to work with asyncio in our specific case.

import socket
import http.client

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler

from .aioclient import parse_headers
from heralding.libs.aiobaserequest import AsyncBaseRequestHandler

# It is a hack in order to get the same class as BaseHTTPRequestHandler,
# but which inherits our AsyncBaseRequestHandler.
AsyncHttpHandler = type('AsyncHttpHandler', (AsyncBaseRequestHandler,),
                        dict(BaseHTTPRequestHandler.__dict__))


class AsyncBaseHTTPRequestHandler(AsyncHttpHandler):
    """Asynchronous analogue of http.server.BaseHTTPRequestHandler."""
    async def parse_request(self):
        self.command = None  # set in case of error on the first line
        self.request_version = version = self.default_request_version
        self.close_connection = True
        requestline = str(self.raw_requestline, 'iso-8859-1')
        requestline = requestline.rstrip('\r\n')
        self.requestline = requestline
        words = requestline.split()
        if len(words) == 3:
            command, path, version = words
            if version[:5] != 'HTTP/':
                self.send_error(
                    HTTPStatus.BAD_REQUEST,
                    "Bad request version (%r)" % version)
                return False
            try:
                base_version_number = version.split('/', 1)[1]
                version_number = base_version_number.split(".")
                if len(version_number) != 2:
                    raise ValueError
                version_number = int(version_number[0]), int(version_number[1])
            except (ValueError, IndexError):
                self.send_error(
                    HTTPStatus.BAD_REQUEST,
                    "Bad request version (%r)" % version)
                return False
            if version_number >= (1, 1) and self.protocol_version >= "HTTP/1.1":
                self.close_connection = False
            if version_number >= (2, 0):
                self.send_error(
                    HTTPStatus.HTTP_VERSION_NOT_SUPPORTED,
                    "Invalid HTTP Version (%s)" % base_version_number)
                return False
        elif len(words) == 2:
            command, path = words
            self.close_connection = True
            if command != 'GET':
                self.send_error(
                    HTTPStatus.BAD_REQUEST,
                    "Bad HTTP/0.9 request type (%r)" % command)
                return False
        elif not words:
            return False
        else:
            self.send_error(
                HTTPStatus.BAD_REQUEST,
                "Bad request syntax (%r)" % requestline)
            return False
        self.command, self.path, self.request_version = command, path, version

        # Examine the headers and look for a Connection directive.
        try:
            self.headers = await parse_headers(self.rfile,
                                               _class=self.MessageClass)
        except http.client.LineTooLong:
            self.send_error(
                HTTPStatus.BAD_REQUEST,
                "Line too long")
            return False
        except http.client.HTTPException as err:
            self.send_error(
                HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE,
                "Too many headers",
                str(err)
            )
            return False

        conntype = self.headers.get('Connection', "")
        if conntype.lower() == 'close':
            self.close_connection = True
        elif (conntype.lower() == 'keep-alive' and
                      self.protocol_version >= "HTTP/1.1"):
            self.close_connection = False
        # Examine the headers and look for an Expect directive
        expect = self.headers.get('Expect', "")
        if (expect.lower() == "100-continue" and
                    self.protocol_version >= "HTTP/1.1" and
                    self.request_version >= "HTTP/1.1"):
            if not self.handle_expect_100():
                return False
        return True

    async def handle_one_request(self):
        try:
            self.raw_requestline = await self.rfile.readline()
            if len(self.raw_requestline) > 65536:
                self.requestline = ''
                self.request_version = ''
                self.command = ''
                self.send_error(HTTPStatus.REQUEST_URI_TOO_LONG)
                return
            if not self.raw_requestline:
                self.close_connection = True
                return
            if not await self.parse_request():
                # An error code has been sent, just exit
                return
            mname = 'do_' + self.command
            if not hasattr(self, mname):
                self.send_error(
                    HTTPStatus.NOT_IMPLEMENTED,
                    "Unsupported method (%r)" % self.command)
                return
            method = getattr(self, mname)
            method()
        except socket.timeout as e:
            #a read or a write timed out.  Discard this connection
            self.log_error("Request timed out: %r", e)
            self.close_connection = True
            return

    async def handle(self):
        self.close_connection = True

        await self.handle_one_request()
        while not self.close_connection:
            await self.handle_one_request()
