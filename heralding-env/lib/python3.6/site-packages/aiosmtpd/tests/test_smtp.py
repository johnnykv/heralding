"""Test the SMTP protocol."""

import time
import socket
import asyncio
import unittest

from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Sink
from aiosmtpd.smtp import SMTP as Server, __ident__ as GREETING
from aiosmtpd.testing.helpers import reset_connection
from contextlib import ExitStack
from smtplib import (
    SMTP, SMTPDataError, SMTPResponseException, SMTPServerDisconnected)
from unittest.mock import Mock, PropertyMock, patch

CRLF = '\r\n'
BCRLF = b'\r\n'


class DecodingController(Controller):
    def factory(self):
        return Server(self.handler, decode_data=True, enable_SMTPUTF8=True)


class NoDecodeController(Controller):
    def factory(self):
        return Server(self.handler, decode_data=False)


class TimeoutController(Controller):
    def factory(self):
        return Server(self.handler, timeout=0.1)


class ReceivingHandler:
    box = None

    def __init__(self):
        self.box = []

    async def handle_DATA(self, server, session, envelope):
        self.box.append(envelope)
        return '250 OK'


class StoreEnvelopeOnVRFYHandler:
    """Saves envelope for later inspection when handling VRFY."""
    envelope = None

    async def handle_VRFY(self, server, session, envelope, addr):
        self.envelope = envelope
        return '250 OK'


class SizedController(Controller):
    def __init__(self, handler, size):
        self.size = size
        super().__init__(handler)

    def factory(self):
        return Server(self.handler, data_size_limit=self.size)


class StrictASCIIController(Controller):
    def factory(self):
        return Server(self.handler, enable_SMTPUTF8=False, decode_data=True)


class CustomHostnameController(Controller):
    def factory(self):
        return Server(self.handler, hostname='custom.localhost')


class CustomIdentController(Controller):
    def factory(self):
        server = Server(self.handler, ident='Identifying SMTP v2112')
        return server


class ErroringHandler:
    error = None

    async def handle_DATA(self, server, session, envelope):
        return '499 Could not accept the message'

    async def handle_exception(self, error):
        self.error = error
        return '500 ErroringHandler handling error'


class ErroringHandlerCustomResponse:
    error = None

    async def handle_exception(self, error):
        self.error = error
        return '451 Temporary error: ({}) {}'.format(
            error.__class__.__name__, str(error))


class ErroringErrorHandler:
    error = None

    async def handle_exception(self, error):
        self.error = error
        raise ValueError('ErroringErrorHandler test')


class UndescribableError(Exception):
    def __str__(self):
        raise Exception()


class UndescribableErrorHandler:
    error = None

    async def handle_exception(self, error):
        self.error = error
        raise UndescribableError()


class ErrorSMTP(Server):
    async def smtp_HELO(self, hostname):
        raise ValueError('test')


class ErrorController(Controller):
    def factory(self):
        return ErrorSMTP(self.handler)


class SleepingHeloHandler:
    async def handle_HELO(self, server, session, envelope, hostname):
        await asyncio.sleep(0.01)
        session.host_name = hostname
        return '250 {}'.format(server.hostname)


class TestProtocol(unittest.TestCase):
    def setUp(self):
        self.transport = Mock()
        self.transport.write = self._write
        self.responses = []
        self._old_loop = asyncio.get_event_loop()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()
        asyncio.set_event_loop(self._old_loop)

    def _write(self, data):
        self.responses.append(data)

    def _get_protocol(self, *args, **kwargs):
        protocol = Server(*args, loop=self.loop, **kwargs)
        protocol.connection_made(self.transport)
        return protocol

    def test_honors_mail_delimeters(self):
        handler = ReceivingHandler()
        data = b'test\r\nmail\rdelimeters\nsaved'
        protocol = self._get_protocol(handler)
        protocol.data_received(BCRLF.join([
            b'HELO example.org',
            b'MAIL FROM: <anne@example.com>',
            b'RCPT TO: <anne@example.com>',
            b'DATA',
            data + b'\r\n.',
            b'QUIT\r\n'
            ]))
        try:
            self.loop.run_until_complete(protocol._handler_coroutine)
        except asyncio.CancelledError:
            pass
        self.assertEqual(len(handler.box), 1)
        self.assertEqual(handler.box[0].content, data)

    def test_empty_email(self):
        handler = ReceivingHandler()
        protocol = self._get_protocol(handler)
        protocol.data_received(BCRLF.join([
            b'HELO example.org',
            b'MAIL FROM: <anne@example.com>',
            b'RCPT TO: <anne@example.com>',
            b'DATA',
            b'.',
            b'QUIT\r\n'
            ]))
        try:
            self.loop.run_until_complete(protocol._handler_coroutine)
        except asyncio.CancelledError:
            pass
        self.assertEqual(self.responses[5], b'250 OK\r\n')
        self.assertEqual(len(handler.box), 1)
        self.assertEqual(handler.box[0].content, b'')


class TestSMTP(unittest.TestCase):
    def setUp(self):
        controller = DecodingController(Sink)
        controller.start()
        self.addCleanup(controller.stop)
        self.address = (controller.hostname, controller.port)

    def test_binary(self):
        with SMTP(*self.address) as client:
            client.sock.send(b"\x80FAIL\r\n")
            code, response = client.getreply()
            self.assertEqual(code, 500)
            self.assertEqual(response, b'Error: bad syntax')

    def test_binary_space(self):
        with SMTP(*self.address) as client:
            client.sock.send(b"\x80 FAIL\r\n")
            code, response = client.getreply()
            self.assertEqual(code, 500)
            self.assertEqual(response, b'Error: bad syntax')

    def test_helo(self):
        with SMTP(*self.address) as client:
            code, response = client.helo('example.com')
            self.assertEqual(code, 250)
            self.assertEqual(response, bytes(socket.getfqdn(), 'utf-8'))

    def test_helo_no_hostname(self):
        with SMTP(*self.address) as client:
            # smtplib substitutes .local_hostname if the argument is falsey.
            client.local_hostname = ''
            code, response = client.helo('')
            self.assertEqual(code, 501)
            self.assertEqual(response, b'Syntax: HELO hostname')

    def test_helo_duplicate(self):
        with SMTP(*self.address) as client:
            code, response = client.helo('example.com')
            self.assertEqual(code, 250)
            code, response = client.helo('example.org')
            self.assertEqual(code, 250)

    def test_ehlo(self):
        with SMTP(*self.address) as client:
            code, response = client.ehlo('example.com')
            self.assertEqual(code, 250)
            lines = response.splitlines()
            self.assertEqual(lines[0], bytes(socket.getfqdn(), 'utf-8'))
            self.assertEqual(lines[1], b'SIZE 33554432')
            self.assertEqual(lines[2], b'SMTPUTF8')
            self.assertEqual(lines[3], b'HELP')

    def test_ehlo_duplicate(self):
        with SMTP(*self.address) as client:
            code, response = client.ehlo('example.com')
            self.assertEqual(code, 250)
            code, response = client.ehlo('example.org')
            self.assertEqual(code, 250)

    def test_ehlo_no_hostname(self):
        with SMTP(*self.address) as client:
            # smtplib substitutes .local_hostname if the argument is falsey.
            client.local_hostname = ''
            code, response = client.ehlo('')
            self.assertEqual(code, 501)
            self.assertEqual(response, b'Syntax: EHLO hostname')

    def test_helo_then_ehlo(self):
        with SMTP(*self.address) as client:
            code, response = client.helo('example.com')
            self.assertEqual(code, 250)
            code, response = client.ehlo('example.org')
            self.assertEqual(code, 250)

    def test_ehlo_then_helo(self):
        with SMTP(*self.address) as client:
            code, response = client.ehlo('example.com')
            self.assertEqual(code, 250)
            code, response = client.helo('example.org')
            self.assertEqual(code, 250)

    def test_noop(self):
        with SMTP(*self.address) as client:
            code, response = client.noop()
            self.assertEqual(code, 250)

    def test_noop_with_arg(self):
        with SMTP(*self.address) as client:
            # .noop() doesn't accept arguments.
            code, response = client.docmd('NOOP', 'ok')
            self.assertEqual(code, 250)

    def test_quit(self):
        client = SMTP(*self.address)
        code, response = client.quit()
        self.assertEqual(code, 221)
        self.assertEqual(response, b'Bye')

    def test_quit_with_arg(self):
        client = SMTP(*self.address)
        code, response = client.docmd('QUIT', 'oops')
        self.assertEqual(code, 501)
        self.assertEqual(response, b'Syntax: QUIT')

    def test_help(self):
        with SMTP(*self.address) as client:
            # Don't get tricked by smtplib processing of the response.
            code, response = client.docmd('HELP')
            self.assertEqual(code, 250)
            self.assertEqual(response,
                             b'Supported commands: DATA EHLO HELO HELP MAIL '
                             b'NOOP QUIT RCPT RSET VRFY')

    def test_help_helo(self):
        with SMTP(*self.address) as client:
            # Don't get tricked by smtplib processing of the response.
            code, response = client.docmd('HELP', 'HELO')
            self.assertEqual(code, 250)
            self.assertEqual(response, b'Syntax: HELO hostname')

    def test_help_ehlo(self):
        with SMTP(*self.address) as client:
            # Don't get tricked by smtplib processing of the response.
            code, response = client.docmd('HELP', 'EHLO')
            self.assertEqual(code, 250)
            self.assertEqual(response, b'Syntax: EHLO hostname')

    def test_help_mail(self):
        with SMTP(*self.address) as client:
            # Don't get tricked by smtplib processing of the response.
            code, response = client.docmd('HELP', 'MAIL')
            self.assertEqual(code, 250)
            self.assertEqual(response, b'Syntax: MAIL FROM: <address>')

    def test_help_mail_esmtp(self):
        with SMTP(*self.address) as client:
            code, response = client.ehlo('example.com')
            self.assertEqual(code, 250)
            code, response = client.docmd('HELP', 'MAIL')
            self.assertEqual(code, 250)
            self.assertEqual(
                response,
                b'Syntax: MAIL FROM: <address> [SP <mail-parameters>]')

    def test_help_rcpt(self):
        with SMTP(*self.address) as client:
            # Don't get tricked by smtplib processing of the response.
            code, response = client.docmd('HELP', 'RCPT')
            self.assertEqual(code, 250)
            self.assertEqual(response, b'Syntax: RCPT TO: <address>')

    def test_help_rcpt_esmtp(self):
        with SMTP(*self.address) as client:
            code, response = client.ehlo('example.com')
            self.assertEqual(code, 250)
            code, response = client.docmd('HELP', 'RCPT')
            self.assertEqual(code, 250)
            self.assertEqual(
                response,
                b'Syntax: RCPT TO: <address> [SP <mail-parameters>]')

    def test_help_data(self):
        with SMTP(*self.address) as client:
            code, response = client.docmd('HELP', 'DATA')
            self.assertEqual(code, 250)
            self.assertEqual(response, b'Syntax: DATA')

    def test_help_rset(self):
        with SMTP(*self.address) as client:
            code, response = client.docmd('HELP', 'RSET')
            self.assertEqual(code, 250)
            self.assertEqual(response, b'Syntax: RSET')

    def test_help_noop(self):
        with SMTP(*self.address) as client:
            code, response = client.docmd('HELP', 'NOOP')
            self.assertEqual(code, 250)
            self.assertEqual(response, b'Syntax: NOOP [ignored]')

    def test_help_quit(self):
        with SMTP(*self.address) as client:
            code, response = client.docmd('HELP', 'QUIT')
            self.assertEqual(code, 250)
            self.assertEqual(response, b'Syntax: QUIT')

    def test_help_vrfy(self):
        with SMTP(*self.address) as client:
            code, response = client.docmd('HELP', 'VRFY')
            self.assertEqual(code, 250)
            self.assertEqual(response, b'Syntax: VRFY <address>')

    def test_help_bad_arg(self):
        with SMTP(*self.address) as client:
            # Don't get tricked by smtplib processing of the response.
            code, response = client.docmd('HELP me!')
            self.assertEqual(code, 501)
            self.assertEqual(response,
                             b'Supported commands: DATA EHLO HELO HELP MAIL '
                             b'NOOP QUIT RCPT RSET VRFY')

    def test_expn(self):
        with SMTP(*self.address) as client:
            code, response = client.expn('anne@example.com')
            self.assertEqual(code, 502)
            self.assertEqual(response, b'EXPN not implemented')

    def test_mail_no_helo(self):
        with SMTP(*self.address) as client:
            code, response = client.docmd('MAIL FROM: <anne@example.com>')
            self.assertEqual(code, 503)
            self.assertEqual(response, b'Error: send HELO first')

    def test_mail_no_arg(self):
        with SMTP(*self.address) as client:
            client.helo('example.com')
            code, response = client.docmd('MAIL')
            self.assertEqual(code, 501)
            self.assertEqual(response, b'Syntax: MAIL FROM: <address>')

    def test_mail_no_from(self):
        with SMTP(*self.address) as client:
            client.helo('example.com')
            code, response = client.docmd('MAIL <anne@example.com>')
            self.assertEqual(code, 501)
            self.assertEqual(response, b'Syntax: MAIL FROM: <address>')

    def test_mail_params_no_esmtp(self):
        with SMTP(*self.address) as client:
            client.helo('example.com')
            code, response = client.docmd(
                'MAIL FROM: <anne@example.com> SIZE=10000')
            self.assertEqual(code, 501)
            self.assertEqual(response, b'Syntax: MAIL FROM: <address>')

    def test_mail_params_esmtp(self):
        with SMTP(*self.address) as client:
            client.ehlo('example.com')
            code, response = client.docmd(
                'MAIL FROM: <anne@example.com> SIZE=10000')
            self.assertEqual(code, 250)
            self.assertEqual(response, b'OK')

    def test_mail_from_twice(self):
        with SMTP(*self.address) as client:
            client.helo('example.com')
            code, response = client.docmd('MAIL FROM: <anne@example.com>')
            self.assertEqual(code, 250)
            self.assertEqual(response, b'OK')
            code, response = client.docmd('MAIL FROM: <anne@example.com>')
            self.assertEqual(code, 503)
            self.assertEqual(response, b'Error: nested MAIL command')

    def test_mail_from_malformed(self):
        with SMTP(*self.address) as client:
            client.helo('example.com')
            code, response = client.docmd('MAIL FROM: Anne <anne@example.com>')
            self.assertEqual(code, 501)
            self.assertEqual(response, b'Syntax: MAIL FROM: <address>')

    def test_mail_malformed_params_esmtp(self):
        with SMTP(*self.address) as client:
            client.ehlo('example.com')
            code, response = client.docmd(
                'MAIL FROM: <anne@example.com> SIZE 10000')
            self.assertEqual(code, 501)
            self.assertEqual(
                response,
                b'Syntax: MAIL FROM: <address> [SP <mail-parameters>]')

    def test_mail_missing_params_esmtp(self):
        with SMTP(*self.address) as client:
            client.ehlo('example.com')
            code, response = client.docmd('MAIL FROM: <anne@example.com> SIZE')
            self.assertEqual(code, 501)
            self.assertEqual(
                response,
                b'Syntax: MAIL FROM: <address> [SP <mail-parameters>]')

    def test_mail_unrecognized_params_esmtp(self):
        with SMTP(*self.address) as client:
            client.ehlo('example.com')
            code, response = client.docmd(
                'MAIL FROM: <anne@example.com> FOO=BAR')
            self.assertEqual(code, 555)
            self.assertEqual(
                response,
                b'MAIL FROM parameters not recognized or not implemented')

    def test_mail_params_bad_syntax_esmtp(self):
        with SMTP(*self.address) as client:
            client.ehlo('example.com')
            code, response = client.docmd(
                'MAIL FROM: <anne@example.com> #$%=!@#')
            self.assertEqual(code, 501)
            self.assertEqual(
                response,
                b'Syntax: MAIL FROM: <address> [SP <mail-parameters>]')

    # Test the workaround http://bugs.python.org/issue27931
    @patch('email._header_value_parser.AngleAddr.addr_spec',
           side_effect=IndexError, new_callable=PropertyMock)
    def test_mail_fail_parse_email(self, addr_spec):
        with SMTP(*self.address) as client:
            client.helo('example.com')
            code, response = client.docmd('MAIL FROM: <""@example.com>')
            self.assertEqual(code, 501)
            self.assertEqual(response, b'Syntax: MAIL FROM: <address>')

    def test_rcpt_no_helo(self):
        with SMTP(*self.address) as client:
            code, response = client.docmd('RCPT TO: <anne@example.com>')
            self.assertEqual(code, 503)
            self.assertEqual(response, b'Error: send HELO first')

    def test_rcpt_no_mail(self):
        with SMTP(*self.address) as client:
            code, response = client.helo('example.com')
            self.assertEqual(code, 250)
            code, response = client.docmd('RCPT TO: <anne@example.com>')
            self.assertEqual(code, 503)
            self.assertEqual(response, b'Error: need MAIL command')

    def test_rcpt_no_arg(self):
        with SMTP(*self.address) as client:
            code, response = client.helo('example.com')
            self.assertEqual(code, 250)
            code, response = client.docmd('MAIL FROM: <anne@example.com>')
            self.assertEqual(code, 250)
            code, response = client.docmd('RCPT')
            self.assertEqual(code, 501)
            self.assertEqual(response, b'Syntax: RCPT TO: <address>')

    def test_rcpt_no_to(self):
        with SMTP(*self.address) as client:
            code, response = client.helo('example.com')
            self.assertEqual(code, 250)
            code, response = client.docmd('MAIL FROM: <anne@example.com>')
            self.assertEqual(code, 250)
            code, response = client.docmd('RCPT <anne@example.com')
            self.assertEqual(code, 501)
            self.assertEqual(response, b'Syntax: RCPT TO: <address>')

    def test_rcpt_no_arg_esmtp(self):
        with SMTP(*self.address) as client:
            code, response = client.ehlo('example.com')
            self.assertEqual(code, 250)
            code, response = client.docmd('MAIL FROM: <anne@example.com>')
            self.assertEqual(code, 250)
            code, response = client.docmd('RCPT')
            self.assertEqual(code, 501)
            self.assertEqual(
                response,
                b'Syntax: RCPT TO: <address> [SP <mail-parameters>]')

    def test_rcpt_no_address(self):
        with SMTP(*self.address) as client:
            code, response = client.ehlo('example.com')
            self.assertEqual(code, 250)
            code, response = client.docmd('MAIL FROM: <anne@example.com>')
            self.assertEqual(code, 250)
            code, response = client.docmd('RCPT TO:')
            self.assertEqual(code, 501)
            self.assertEqual(
                response,
                b'Syntax: RCPT TO: <address> [SP <mail-parameters>]')

    def test_rcpt_with_params_no_esmtp(self):
        with SMTP(*self.address) as client:
            code, response = client.helo('example.com')
            self.assertEqual(code, 250)
            code, response = client.docmd('MAIL FROM: <anne@example.com>')
            self.assertEqual(code, 250)
            code, response = client.docmd(
                'RCPT TO: <bart@example.com> SIZE=1000')
            self.assertEqual(code, 501)
            self.assertEqual(response, b'Syntax: RCPT TO: <address>')

    def test_rcpt_with_bad_params(self):
        with SMTP(*self.address) as client:
            code, response = client.ehlo('example.com')
            self.assertEqual(code, 250)
            code, response = client.docmd('MAIL FROM: <anne@example.com>')
            self.assertEqual(code, 250)
            code, response = client.docmd(
                'RCPT TO: <bart@example.com> #$%=!@#')
            self.assertEqual(code, 501)
            self.assertEqual(
                response,
                b'Syntax: RCPT TO: <address> [SP <mail-parameters>]')

    def test_rcpt_with_unknown_params(self):
        with SMTP(*self.address) as client:
            code, response = client.ehlo('example.com')
            self.assertEqual(code, 250)
            code, response = client.docmd('MAIL FROM: <anne@example.com>')
            self.assertEqual(code, 250)
            code, response = client.docmd(
                'RCPT TO: <bart@example.com> FOOBAR')
            self.assertEqual(code, 555)
            self.assertEqual(
                response,
                b'RCPT TO parameters not recognized or not implemented')

    # Test the workaround http://bugs.python.org/issue27931
    @patch('email._header_value_parser.AngleAddr.addr_spec',
           new_callable=PropertyMock)
    def test_rcpt_fail_parse_email(self, addr_spec):
        with SMTP(*self.address) as client:
            code, response = client.ehlo('example.com')
            self.assertEqual(code, 250)
            code, response = client.docmd('MAIL FROM: <anne@example.com>')
            self.assertEqual(code, 250)
            addr_spec.side_effect = IndexError
            code, response = client.docmd('RCPT TO: <""@example.com>')
            self.assertEqual(code, 501)
            self.assertEqual(
                response,
                b'Syntax: RCPT TO: <address> [SP <mail-parameters>]')

    def test_rset(self):
        with SMTP(*self.address) as client:
            code, response = client.rset()
            self.assertEqual(code, 250)
            self.assertEqual(response, b'OK')

    def test_rset_with_arg(self):
        with SMTP(*self.address) as client:
            code, response = client.docmd('RSET FOO')
            self.assertEqual(code, 501)
            self.assertEqual(response, b'Syntax: RSET')

    def test_vrfy(self):
        with SMTP(*self.address) as client:
            code, response = client.docmd('VRFY <anne@example.com>')
            self.assertEqual(code, 252)
            self.assertEqual(
              response,
              b'Cannot VRFY user, but will accept message and attempt delivery'
              )

    def test_vrfy_no_arg(self):
        with SMTP(*self.address) as client:
            code, response = client.docmd('VRFY')
            self.assertEqual(code, 501)
            self.assertEqual(response, b'Syntax: VRFY <address>')

    def test_vrfy_not_an_address(self):
        with SMTP(*self.address) as client:
            code, response = client.docmd('VRFY @@')
            self.assertEqual(code, 502)
            self.assertEqual(response, b'Could not VRFY @@')

    def test_data_no_helo(self):
        with SMTP(*self.address) as client:
            code, response = client.docmd('DATA')
            self.assertEqual(code, 503)
            self.assertEqual(response, b'Error: send HELO first')

    def test_data_no_rcpt(self):
        with SMTP(*self.address) as client:
            code, response = client.helo('example.com')
            self.assertEqual(code, 250)
            code, response = client.docmd('DATA')
            self.assertEqual(code, 503)
            self.assertEqual(response, b'Error: need RCPT command')

    def test_data_invalid_params(self):
        with SMTP(*self.address) as client:
            code, response = client.helo('example.com')
            self.assertEqual(code, 250)
            code, response = client.docmd('MAIL FROM: <anne@example.com>')
            self.assertEqual(code, 250)
            code, response = client.docmd('RCPT TO: <anne@example.com>')
            self.assertEqual(code, 250)
            code, response = client.docmd('DATA FOOBAR')
            self.assertEqual(code, 501)
            self.assertEqual(response, b'Syntax: DATA')

    def test_empty_command(self):
        with SMTP(*self.address) as client:
            code, response = client.docmd('')
            self.assertEqual(code, 500)
            self.assertEqual(response, b'Error: bad syntax')

    def test_too_long_command(self):
        with SMTP(*self.address) as client:
            code, response = client.docmd('a' * 513)
            self.assertEqual(code, 500)
            self.assertEqual(response, b'Error: line too long')

    def test_unknown_command(self):
        with SMTP(*self.address) as client:
            code, response = client.docmd('FOOBAR')
            self.assertEqual(code, 500)
            self.assertEqual(
                response,
                b'Error: command "FOOBAR" not recognized')


class TestResetCommands(unittest.TestCase):
    """Test that sender and recipients are reset on RSET, HELO, and EHLO.

    The tests below issue each command twice with different addresses and
    verify that mail_from and rcpt_tos have been replacecd.
    """
    expected_envelope_data = [
        # Pre-RSET/HELO/EHLO envelope data.
        dict(
            mail_from='anne@example.com',
            rcpt_tos=['bart@example.com', 'cate@example.com'],
            ),
        dict(
            mail_from='dave@example.com',
            rcpt_tos=['elle@example.com', 'fred@example.com'],
            ),
        ]

    def setUp(self):
        self._handler = StoreEnvelopeOnVRFYHandler()
        self._controller = DecodingController(self._handler)
        self._controller.start()
        self._address = (self._controller.hostname, self._controller.port)
        self.addCleanup(self._controller.stop)

    def _send_envelope_data(self, client, mail_from, rcpt_tos):
        client.mail(mail_from)
        for rcpt in rcpt_tos:
            client.rcpt(rcpt)

    def test_helo(self):
        with SMTP(*self._address) as client:
            # Each time through the loop, the HELO will reset the envelope.
            for data in self.expected_envelope_data:
                client.helo('example.com')
                # Save the envelope in the handler.
                client.vrfy('zuzu@example.com')
                self.assertIsNone(self._handler.envelope.mail_from)
                self.assertEqual(len(self._handler.envelope.rcpt_tos), 0)
                self._send_envelope_data(client, **data)
                client.vrfy('zuzu@example.com')
                self.assertEqual(
                    self._handler.envelope.mail_from, data['mail_from'])
                self.assertEqual(
                    self._handler.envelope.rcpt_tos, data['rcpt_tos'])

    def test_ehlo(self):
        with SMTP(*self._address) as client:
            # Each time through the loop, the EHLO will reset the envelope.
            for data in self.expected_envelope_data:
                client.ehlo('example.com')
                # Save the envelope in the handler.
                client.vrfy('zuzu@example.com')
                self.assertIsNone(self._handler.envelope.mail_from)
                self.assertEqual(len(self._handler.envelope.rcpt_tos), 0)
                self._send_envelope_data(client, **data)
                client.vrfy('zuzu@example.com')
                self.assertEqual(
                    self._handler.envelope.mail_from, data['mail_from'])
                self.assertEqual(
                    self._handler.envelope.rcpt_tos, data['rcpt_tos'])

    def test_rset(self):
        with SMTP(*self._address) as client:
            client.helo('example.com')
            # Each time through the loop, the RSET will reset the envelope.
            for data in self.expected_envelope_data:
                self._send_envelope_data(client, **data)
                # Save the envelope in the handler.
                client.vrfy('zuzu@example.com')
                self.assertEqual(
                    self._handler.envelope.mail_from, data['mail_from'])
                self.assertEqual(
                    self._handler.envelope.rcpt_tos, data['rcpt_tos'])
                # Reset the envelope explicitly.
                client.rset()
                client.vrfy('zuzu@example.com')
                self.assertIsNone(self._handler.envelope.mail_from)
                self.assertEqual(len(self._handler.envelope.rcpt_tos), 0)


class TestSMTPWithController(unittest.TestCase):
    def test_mail_with_size_too_large(self):
        controller = SizedController(Sink(), 9999)
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            client.ehlo('example.com')
            code, response = client.docmd(
                'MAIL FROM: <anne@example.com> SIZE=10000')
            self.assertEqual(code, 552)
            self.assertEqual(
                response,
                b'Error: message size exceeds fixed maximum message size')

    def test_mail_with_compatible_smtputf8(self):
        handler = ReceivingHandler()
        controller = Controller(handler)
        controller.start()
        self.addCleanup(controller.stop)
        recipient = 'bart\xCB@example.com'
        sender = 'anne\xCB@example.com'
        with SMTP(controller.hostname, controller.port) as client:
            client.ehlo('example.com')
            client.send(bytes(
                'MAIL FROM: <' + sender + '> SMTPUTF8\r\n',
                encoding='utf-8'))
            code, response = client.getreply()
            self.assertEqual(code, 250)
            self.assertEqual(response, b'OK')
            client.send(bytes(
                'RCPT TO: <' + recipient + '>\r\n',
                encoding='utf-8'))
            code, response = client.getreply()
            self.assertEqual(code, 250)
            self.assertEqual(response, b'OK')
            code, response = client.data('')
            self.assertEqual(code, 250)
            self.assertEqual(response, b'OK')
        self.assertEqual(handler.box[0].rcpt_tos[0], recipient)
        self.assertEqual(handler.box[0].mail_from, sender)

    def test_mail_with_unrequited_smtputf8(self):
        controller = Controller(Sink())
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            client.ehlo('example.com')
            code, response = client.docmd('MAIL FROM: <anne@example.com>')
            self.assertEqual(code, 250)
            self.assertEqual(response, b'OK')

    def test_mail_with_incompatible_smtputf8(self):
        controller = Controller(Sink())
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            client.ehlo('example.com')
            code, response = client.docmd(
                'MAIL FROM: <anne@example.com> SMTPUTF8=YES')
            self.assertEqual(code, 501)
            self.assertEqual(response, b'Error: SMTPUTF8 takes no arguments')

    def test_mail_invalid_body(self):
        controller = Controller(Sink())
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            client.ehlo('example.com')
            code, response = client.docmd(
                'MAIL FROM: <anne@example.com> BODY 9BIT')
            self.assertEqual(code, 501)
            self.assertEqual(response,
                             b'Error: BODY can only be one of 7BIT, 8BITMIME')

    def test_esmtp_no_size_limit(self):
        controller = SizedController(Sink(), size=None)
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            code, response = client.ehlo('example.com')
            self.assertEqual(code, 250)
            for line in response.splitlines():
                self.assertNotEqual(line[:4], b'SIZE')

    def test_process_message_error(self):
        controller = Controller(ErroringHandler())
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            code, response = client.ehlo('example.com')
            self.assertEqual(code, 250)
            with self.assertRaises(SMTPDataError) as cm:
                client.sendmail('anne@example.com', ['bart@example.com'], """\
From: anne@example.com
To: bart@example.com
Subject: A test

Testing
""")
            self.assertEqual(cm.exception.smtp_code, 499)
            self.assertEqual(cm.exception.smtp_error,
                             b'Could not accept the message')

    def test_too_long_message_body(self):
        controller = SizedController(Sink(), size=100)
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            client.helo('example.com')
            mail = '\r\n'.join(['z' * 20] * 10)
            with self.assertRaises(SMTPResponseException) as cm:
                client.sendmail('anne@example.com', ['bart@example.com'], mail)
            self.assertEqual(cm.exception.smtp_code, 552)
            self.assertEqual(cm.exception.smtp_error,
                             b'Error: Too much mail data')

    def test_dots_escaped(self):
        handler = ReceivingHandler()
        controller = DecodingController(handler)
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            client.helo('example.com')
            mail = CRLF.join(['Test', '.', 'mail'])
            client.sendmail('anne@example.com', ['bart@example.com'], mail)
            self.assertEqual(len(handler.box), 1)
            self.assertEqual(handler.box[0].content, 'Test\r\n.\r\nmail')

    def test_unexpected_errors(self):
        handler = ErroringHandler()
        controller = ErrorController(handler)
        controller.start()
        self.addCleanup(controller.stop)
        with ExitStack() as resources:
            # Suppress logging to the console during the tests.  Depending on
            # timing, the exception may or may not be logged.
            resources.enter_context(patch('aiosmtpd.smtp.log.exception'))
            client = resources.enter_context(
                SMTP(controller.hostname, controller.port))
            code, response = client.helo('example.com')
        self.assertEqual(code, 500)
        self.assertEqual(response, b'ErroringHandler handling error')
        self.assertIsInstance(handler.error, ValueError)

    def test_unexpected_errors_unhandled(self):
        handler = Sink()
        handler.error = None
        controller = ErrorController(handler)
        controller.start()
        self.addCleanup(controller.stop)
        with ExitStack() as resources:
            # Suppress logging to the console during the tests.  Depending on
            # timing, the exception may or may not be logged.
            resources.enter_context(patch('aiosmtpd.smtp.log.exception'))
            client = resources.enter_context(
                SMTP(controller.hostname, controller.port))
            code, response = client.helo('example.com')
        self.assertEqual(code, 500)
        self.assertEqual(response, b'Error: (ValueError) test')
        # handler.error did not change because the handler does not have a
        # handle_exception() method.
        self.assertIsNone(handler.error)

    def test_unexpected_errors_custom_response(self):
        handler = ErroringHandlerCustomResponse()
        controller = ErrorController(handler)
        controller.start()
        self.addCleanup(controller.stop)
        with ExitStack() as resources:
            # Suppress logging to the console during the tests.  Depending on
            # timing, the exception may or may not be logged.
            resources.enter_context(patch('aiosmtpd.smtp.log.exception'))
            client = resources.enter_context(
                SMTP(controller.hostname, controller.port))
            code, response = client.helo('example.com')
        self.assertEqual(code, 451)
        self.assertEqual(response, b'Temporary error: (ValueError) test')
        self.assertIsInstance(handler.error, ValueError)

    def test_exception_handler_exception(self):
        handler = ErroringErrorHandler()
        controller = ErrorController(handler)
        controller.start()
        self.addCleanup(controller.stop)
        with ExitStack() as resources:
            # Suppress logging to the console during the tests.  Depending on
            # timing, the exception may or may not be logged.
            resources.enter_context(patch('aiosmtpd.smtp.log.exception'))
            client = resources.enter_context(
                SMTP(controller.hostname, controller.port))
            code, response = client.helo('example.com')
        self.assertEqual(code, 500)
        self.assertEqual(response,
                         b'Error: (ValueError) ErroringErrorHandler test')
        self.assertIsInstance(handler.error, ValueError)

    def test_exception_handler_undescribable(self):
        handler = UndescribableErrorHandler()
        controller = ErrorController(handler)
        controller.start()
        self.addCleanup(controller.stop)
        with ExitStack() as resources:
            # Suppress logging to the console during the tests.  Depending on
            # timing, the exception may or may not be logged.
            resources.enter_context(patch('aiosmtpd.smtp.log.exception'))
            client = resources.enter_context(
                SMTP(controller.hostname, controller.port))
            code, response = client.helo('example.com')
        self.assertEqual(code, 500)
        self.assertEqual(response, b'Error: Cannot describe error')
        self.assertIsInstance(handler.error, ValueError)

    def test_bad_encodings(self):
        handler = ReceivingHandler()
        controller = DecodingController(handler)
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            client.helo('example.com')
            mail_from = b'anne\xFF@example.com'
            mail_to = b'bart\xFF@example.com'
            client.ehlo('test')
            client.send(b'MAIL FROM:' + mail_from + b'\r\n')
            code, response = client.getreply()
            self.assertEqual(code, 250)
            client.send(b'RCPT TO:' + mail_to + b'\r\n')
            code, response = client.getreply()
            self.assertEqual(code, 250)
            client.data('Test mail')
            self.assertEqual(len(handler.box), 1)
            envelope = handler.box[0]
            mail_from2 = envelope.mail_from.encode(
                'utf-8', errors='surrogateescape')
            self.assertEqual(mail_from2, mail_from)
            mail_to2 = envelope.rcpt_tos[0].encode(
                'utf-8', errors='surrogateescape')
            self.assertEqual(mail_to2, mail_to)


class TestCustomizations(unittest.TestCase):
    def test_custom_hostname(self):
        controller = CustomHostnameController(Sink())
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            code, response = client.helo('example.com')
            self.assertEqual(code, 250)
            self.assertEqual(response, bytes('custom.localhost', 'utf-8'))

    def test_custom_greeting(self):
        controller = CustomIdentController(Sink())
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP() as client:
            code, msg = client.connect(controller.hostname, controller.port)
            self.assertEqual(code, 220)
            # The hostname prefix is unpredictable.
            self.assertEqual(msg[-22:], b'Identifying SMTP v2112')

    def test_default_greeting(self):
        controller = Controller(Sink())
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP() as client:
            code, msg = client.connect(controller.hostname, controller.port)
            self.assertEqual(code, 220)
            # The hostname prefix is unpredictable.
            self.assertEqual(msg[-len(GREETING):], bytes(GREETING, 'utf-8'))

    def test_mail_invalid_body_param(self):
        controller = NoDecodeController(Sink())
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP() as client:
            code, msg = client.connect(controller.hostname, controller.port)
            client.ehlo('example.com')
            code, response = client.docmd(
                'MAIL FROM: <anne@example.com> BODY=FOOBAR')
            self.assertEqual(code, 501)
            self.assertEqual(
                response,
                b'Error: BODY can only be one of 7BIT, 8BITMIME')


class TestClientCrash(unittest.TestCase):
    # GH#62 - if the client crashes during the SMTP dialog we want to make
    # sure we don't get tracebacks where we call readline().
    def setUp(self):
        controller = Controller(Sink)
        controller.start()
        self.addCleanup(controller.stop)
        self.address = (controller.hostname, controller.port)

    def test_connection_reset_during_DATA(self):
        with SMTP(*self.address) as client:
            client.helo('example.com')
            client.docmd('MAIL FROM: <anne@example.com>')
            client.docmd('RCPT TO: <bart@example.com>')
            client.docmd('DATA')
            # Start sending the DATA but reset the connection before that
            # completes, i.e. before the .\r\n
            client.send(b'From: <anne@example.com>')
            reset_connection(client)
            # The connection should be disconnected, so trying to do another
            # command from here will give us an exception.  In GH#62, the
            # server just hung.
            self.assertRaises(SMTPServerDisconnected, client.noop)

    def test_connection_reset_during_command(self):
        with SMTP(*self.address) as client:
            client.helo('example.com')
            # Start sending a command but reset the connection before that
            # completes, i.e. before the \r\n
            client.send('MAIL FROM: <anne')
            reset_connection(client)
            # The connection should be disconnected, so trying to do another
            # command from here will give us an exception.  In GH#62, the
            # server just hung.
            self.assertRaises(SMTPServerDisconnected, client.noop)

    def test_close_in_command(self):
        with SMTP(*self.address) as client:
            # Don't include the CRLF.
            client.send('FOO')
            client.close()

    def test_close_in_data(self):
        with SMTP(*self.address) as client:
            code, response = client.helo('example.com')
            self.assertEqual(code, 250)
            code, response = client.docmd('MAIL FROM: <anne@example.com>')
            self.assertEqual(code, 250)
            code, response = client.docmd('RCPT TO: <bart@example.com>')
            self.assertEqual(code, 250)
            code, response = client.docmd('DATA')
            self.assertEqual(code, 354)
            # Don't include the CRLF.
            client.send('FOO')
            client.close()


class TestStrictASCII(unittest.TestCase):
    def setUp(self):
        controller = StrictASCIIController(Sink())
        controller.start()
        self.addCleanup(controller.stop)
        self.address = (controller.hostname, controller.port)

    def test_ehlo(self):
        with SMTP(*self.address) as client:
            code, response = client.ehlo('example.com')
            self.assertEqual(code, 250)
            lines = response.splitlines()
            self.assertNotIn(b'SMTPUTF8', lines)

    def test_bad_encoded_param(self):
        with SMTP(*self.address) as client:
            client.ehlo('example.com')
            client.send(b'MAIL FROM: <anne\xFF@example.com>\r\n')
            code, response = client.getreply()
            self.assertEqual(code, 500)
            self.assertIn(b'Error: strict ASCII mode', response)

    def test_mail_param(self):
        with SMTP(*self.address) as client:
            client.ehlo('example.com')
            code, response = client.docmd(
                'MAIL FROM: <anne@example.com> SMTPUTF8')
            self.assertEqual(code, 501)
            self.assertEqual(response, b'Error: SMTPUTF8 disabled')

    def test_data(self):
        with SMTP(*self.address) as client:
            code, response = client.ehlo('example.com')
            self.assertEqual(code, 250)
            with self.assertRaises(SMTPDataError) as cm:
                client.sendmail('anne@example.com', ['bart@example.com'], b"""\
From: anne@example.com
To: bart@example.com
Subject: A test

Testing\xFF
""")
            self.assertEqual(cm.exception.smtp_code, 500)
            self.assertIn(b'Error: strict ASCII mode', cm.exception.smtp_error)


class TestSleepingHandler(unittest.TestCase):
    def setUp(self):
        controller = NoDecodeController(SleepingHeloHandler())
        controller.start()
        self.addCleanup(controller.stop)
        self.address = (controller.hostname, controller.port)

    def test_close_after_helo(self):
        with SMTP(*self.address) as client:
            client.send('HELO example.com\r\n')
            client.sock.shutdown(socket.SHUT_WR)
            self.assertRaises(SMTPServerDisconnected, client.getreply)


class TestTimeout(unittest.TestCase):
    def setUp(self):
        controller = TimeoutController(Sink)
        controller.start()
        self.addCleanup(controller.stop)
        self.address = (controller.hostname, controller.port)

    def test_timeout(self):
        with SMTP(*self.address) as client:
            code, response = client.ehlo('example.com')
            time.sleep(0.3)
            self.assertRaises(SMTPServerDisconnected, client.getreply)
