"""Test SMTP over SSL/TLS."""

import ssl
import socket
import unittest
import pkg_resources

from aiosmtpd.controller import Controller as BaseController
from aiosmtpd.smtp import SMTP as SMTPProtocol
from email.mime.text import MIMEText
from smtplib import SMTP_SSL


class Controller(BaseController):
    def factory(self):
        return SMTPProtocol(self.handler)


class ReceivingHandler:
    def __init__(self):
        self.box = []

    async def handle_DATA(self, server, session, envelope):
        self.box.append(envelope)
        return '250 OK'


def get_server_context():
    tls_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    tls_context.load_cert_chain(
        pkg_resources.resource_filename('aiosmtpd.tests.certs', 'server.crt'),
        pkg_resources.resource_filename('aiosmtpd.tests.certs', 'server.key'))
    return tls_context


def get_client_context():
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    context.check_hostname = False
    context.load_verify_locations(
        cafile=pkg_resources.resource_filename(
            'aiosmtpd.tests.certs', 'server.crt'))
    return context


class TestSMTPS(unittest.TestCase):
    def setUp(self):
        self.handler = ReceivingHandler()
        controller = Controller(self.handler, ssl_context=get_server_context())
        controller.start()
        self.addCleanup(controller.stop)
        self.address = (controller.hostname, controller.port)

    def test_smtps(self):
        with SMTP_SSL(*self.address, context=get_client_context()) as client:
            code, response = client.helo('example.com')
            self.assertEqual(code, 250)
            self.assertEqual(response, socket.getfqdn().encode('utf-8'))
            client.send_message(
                MIMEText('hi'), 'sender@example.com', 'rcpt1@example.com')
        self.assertEqual(len(self.handler.box), 1)
        envelope = self.handler.box[0]
        self.assertEqual(envelope.mail_from, 'sender@example.com')
