"""Test other aspects of the server implementation."""


import socket
import unittest

from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Sink
from aiosmtpd.smtp import SMTP as Server
from smtplib import SMTP


class TestServer(unittest.TestCase):
    def test_smtp_utf8(self):
        controller = Controller(Sink())
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            code, response = client.ehlo('example.com')
        self.assertEqual(code, 250)
        self.assertIn(b'SMTPUTF8', response.splitlines())

    def test_default_max_command_size_limit(self):
        server = Server(Sink())
        self.assertEqual(server.max_command_size_limit, 512)

    def test_special_max_command_size_limit(self):
        server = Server(Sink())
        server.command_size_limits['DATA'] = 1024
        self.assertEqual(server.max_command_size_limit, 1024)

    def test_socket_error(self):
        # Testing starting a server with a port already in use
        s1 = Controller(Sink(), port=8025)
        s2 = Controller(Sink(), port=8025)
        self.addCleanup(s1.stop)
        self.addCleanup(s2.stop)
        s1.start()
        self.assertRaises(socket.error, s2.start)

    def test_server_attribute(self):
        controller = Controller(Sink())
        self.assertIsNone(controller.server)
        try:
            controller.start()
            self.assertIsNotNone(controller.server)
        finally:
            controller.stop()
            self.assertIsNone(controller.server)
