import ssl
import unittest
import pkg_resources

from aiosmtpd.controller import Controller as BaseController
from aiosmtpd.handlers import Sink
from aiosmtpd.smtp import SMTP as SMTPProtocol
from email.mime.text import MIMEText
from smtplib import SMTP


class Controller(BaseController):
    def factory(self):
        return SMTPProtocol(self.handler)


class ReceivingHandler:
    def __init__(self):
        self.box = []

    async def handle_DATA(self, server, session, envelope):
        self.box.append(envelope)
        return '250 OK'


def get_tls_context():
    tls_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    tls_context.load_cert_chain(
        pkg_resources.resource_filename('aiosmtpd.tests.certs', 'server.crt'),
        pkg_resources.resource_filename('aiosmtpd.tests.certs', 'server.key'))
    return tls_context


class TLSRequiredController(Controller):
    def factory(self):
        return SMTPProtocol(
            self.handler,
            decode_data=True,
            require_starttls=True,
            tls_context=get_tls_context())


class TLSController(Controller):
    def factory(self):
        return SMTPProtocol(
            self.handler,
            decode_data=True,
            require_starttls=False,
            tls_context=get_tls_context())


class HandshakeFailingHandler:
    def handle_STARTTLS(self, server, session, envelope):
        return False


class TestStartTLS(unittest.TestCase):
    def test_starttls(self):
        handler = ReceivingHandler()
        controller = TLSController(handler)
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            code, response = client.ehlo('example.com')
            self.assertEqual(code, 250)
            self.assertIn('starttls', client.esmtp_features)
            code, response = client.starttls()
            self.assertEqual(code, 220)
            client.send_message(
                MIMEText('hi'),
                'sender@example.com',
                'rcpt1@example.com')
        self.assertEqual(len(handler.box), 1)

    def test_failed_handshake(self):
        controller = TLSController(HandshakeFailingHandler())
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            client.ehlo('example.com')
            code, response = client.starttls()
            self.assertEqual(code, 220)
            code, response = client.mail('sender@example.com')
            self.assertEqual(code, 554)
            code, response = client.rcpt('rcpt@example.com')
            self.assertEqual(code, 554)

    def test_disabled_tls(self):
        controller = Controller(Sink)
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            client.ehlo('example.com')
            code, response = client.docmd('STARTTLS')
            self.assertEqual(code, 454)

    def test_tls_bad_syntax(self):
        controller = TLSController(Sink)
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            client.ehlo('example.com')
            code, response = client.docmd('STARTTLS', 'TRUE')
            self.assertEqual(code, 501)

    def test_help_after_starttls(self):
        controller = TLSController(Sink())
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            # Don't get tricked by smtplib processing of the response.
            code, response = client.docmd('HELP')
            self.assertEqual(code, 250)
            self.assertEqual(response,
                             b'Supported commands: DATA EHLO HELO HELP MAIL '
                             b'NOOP QUIT RCPT RSET STARTTLS VRFY')


class TestTLSForgetsSessionData(unittest.TestCase):
    def setUp(self):
        controller = TLSController(Sink)
        controller.start()
        self.addCleanup(controller.stop)
        self.address = (controller.hostname, controller.port)

    def test_forget_ehlo(self):
        with SMTP(*self.address) as client:
            client.starttls()
            code, response = client.mail('sender@example.com')
            self.assertEqual(code, 503)
            self.assertEqual(response, b'Error: send HELO first')

    def test_forget_mail(self):
        with SMTP(*self.address) as client:
            client.ehlo('example.com')
            client.mail('sender@example.com')
            client.starttls()
            client.ehlo('example.com')
            code, response = client.rcpt('rcpt@example.com')
            self.assertEqual(code, 503)
            self.assertEqual(response, b'Error: need MAIL command')

    def test_forget_rcpt(self):
        with SMTP(*self.address) as client:
            client.ehlo('example.com')
            client.mail('sender@example.com')
            client.rcpt('rcpt@example.com')
            client.starttls()
            client.ehlo('example.com')
            client.mail('sender@example.com')
            code, response = client.docmd('DATA')
            self.assertEqual(code, 503)
            self.assertEqual(response, b'Error: need RCPT command')


class TestRequireTLS(unittest.TestCase):
    def setUp(self):
        controller = TLSRequiredController(Sink)
        controller.start()
        self.addCleanup(controller.stop)
        self.address = (controller.hostname, controller.port)

    def test_hello_fails(self):
        with SMTP(*self.address) as client:
            code, response = client.helo('example.com')
            self.assertEqual(code, 530)

    def test_help_fails(self):
        with SMTP(*self.address) as client:
            code, response = client.docmd('HELP', 'HELO')
            self.assertEqual(code, 530)

    def test_ehlo(self):
        with SMTP(*self.address) as client:
            code, response = client.ehlo('example.com')
            self.assertEqual(code, 250)
            self.assertIn('starttls', client.esmtp_features)

    def test_mail_fails(self):
        with SMTP(*self.address) as client:
            client.ehlo('example.com')
            code, response = client.mail('sender@exapmle.com')
            self.assertEqual(code, 530)

    def test_rcpt_fails(self):
        with SMTP(*self.address) as client:
            client.ehlo('example.com')
            code, response = client.rcpt('sender@exapmle.com')
            self.assertEqual(code, 530)

    def test_vrfy_fails(self):
        with SMTP(*self.address) as client:
            client.ehlo('example.com')
            code, response = client.vrfy('sender@exapmle.com')
            self.assertEqual(code, 530)

    def test_data_fails(self):
        with SMTP(*self.address) as client:
            client.ehlo('example.com')
            code, response = client.docmd('DATA')
            self.assertEqual(code, 530)
