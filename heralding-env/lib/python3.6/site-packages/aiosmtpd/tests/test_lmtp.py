"""Test the LMTP protocol."""

import socket
import unittest

from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Sink
from aiosmtpd.lmtp import LMTP
from smtplib import SMTP


class LMTPController(Controller):
    def factory(self):
        return LMTP(self.handler)


class TestLMTP(unittest.TestCase):
    def setUp(self):
        controller = LMTPController(Sink)
        controller.start()
        self.address = (controller.hostname, controller.port)
        self.addCleanup(controller.stop)

    def test_lhlo(self):
        with SMTP(*self.address) as client:
            code, response = client.docmd('LHLO', 'example.com')
            self.assertEqual(code, 250)
            self.assertEqual(response, bytes(socket.getfqdn(), 'utf-8'))

    def test_helo(self):
        # HELO and EHLO are not valid LMTP commands.
        with SMTP(*self.address) as client:
            code, response = client.helo('example.com')
            self.assertEqual(code, 500)
            self.assertEqual(response, b'Error: command "HELO" not recognized')

    def test_ehlo(self):
        # HELO and EHLO are not valid LMTP commands.
        with SMTP(*self.address) as client:
            code, response = client.ehlo('example.com')
            self.assertEqual(code, 500)
            self.assertEqual(response, b'Error: command "EHLO" not recognized')

    def test_help(self):
        # https://github.com/aio-libs/aiosmtpd/issues/113
        with SMTP(*self.address) as client:
            # Don't get tricked by smtplib processing of the response.
            code, response = client.docmd('HELP')
            self.assertEqual(code, 250)
            self.assertEqual(response,
                             b'Supported commands: DATA HELP LHLO MAIL '
                             b'NOOP QUIT RCPT RSET VRFY')
