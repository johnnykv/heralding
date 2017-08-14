# Copyright (C) 2012 Aniket Panse <contact@aniketpanse.in
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

import hmac
import base64
import asyncio
import smtplib
import unittest

from heralding.capabilities import smtp
from heralding.reporting.reporting_relay import ReportingRelay


class SmtpTests(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(None)

        self.reporting_relay = ReportingRelay()
        self.reporting_relay_task = self.loop.run_in_executor(None, self.reporting_relay.start)

    def tearDown(self):
        self.reporting_relay.stop()
        # We give reporting_relay a chance to be finished
        self.loop.run_until_complete(self.reporting_relay_task)

        self.server.close()
        self.loop.run_until_complete(self.server.wait_closed())

        self.loop.close()

    def test_connection(self):
        """ Tries to connect and run a EHLO command. Very basic test.
        """
        def smtp_connection():
            smtp_ = smtplib.SMTP('127.0.0.1', 8888, local_hostname='localhost', timeout=15)
            smtp_.ehlo()
            smtp_.quit()

        # Use uncommon port so that we can run test even if the Honeypot is running.
        options = {'enabled': 'True', 'port': 8888, 'protocol_specific_data': {'banner': 'test'},
                   'users': {'test': 'test'}, }
        smtp_cap = smtp.smtp(options, self.loop)

        server_coro = asyncio.start_server(smtp_cap.handle_session, '0.0.0.0', 8888, loop=self.loop)
        self.server = self.loop.run_until_complete(server_coro)

        smtp_task = self.loop.run_in_executor(None, smtp_connection)
        self.loop.run_until_complete(smtp_task)


    def test_AUTH_CRAM_MD5_reject(self):
        """ Makes sure the server rejects all invalid login attempts that use the
            CRAM-MD5 Authentication method.
        """
        def encode_cram_md5(challenge, user, password):
            challenge = base64.decodebytes(challenge)
            response = user + b' ' + bytes(hmac.HMAC(password, challenge).hexdigest(), 'utf-8')
            return str(base64.b64encode(response), 'utf-8')

        def smtp_auth_cram_md5():
            smtp_ = smtplib.SMTP('127.0.0.1', 8888, local_hostname='localhost', timeout=15)
            _, resp = smtp_.docmd('AUTH', 'CRAM-MD5')
            code, resp = smtp_.docmd(encode_cram_md5(resp, b'test', b'test'))
            smtp_.quit()
            # For now, the server's going to return a 535 code.
            self.assertEqual(code, 535)

        options = {'enabled': 'True', 'port': 8888, 'protocol_specific_data': {'banner': 'Test'},
                   'users': {'someguy': 'test'}}
        smtp_cap = smtp.smtp(options, self.loop)

        server_coro = asyncio.start_server(smtp_cap.handle_session, '0.0.0.0', 8888, loop=self.loop)
        self.server = self.loop.run_until_complete(server_coro)

        smtp_task = self.loop.run_in_executor(None, smtp_auth_cram_md5)
        self.loop.run_until_complete(smtp_task)


    def test_AUTH_PLAIN_reject(self):
        """ Makes sure the server rejects all invalid login attempts that use the PLAIN Authentication method.
        """
        def smtp_auth_plain_reject():
            smtp_ = smtplib.SMTP('127.0.0.1', 8888, local_hostname='localhost', timeout=15)
            arg = bytes('\0{0}\0{1}'.format('test', 'test'), 'utf-8')
            code, _ = smtp_.docmd('AUTH', 'PLAIN ' + str(base64.b64encode(arg), 'utf-8'))
            smtp_.quit()
            self.assertEqual(code, 535)

        options = {'enabled': 'True', 'port': 0, 'protocol_specific_data': {'banner': 'Test'},
                   'users': {'someguy': 'test'}}

        smtp_cap = smtp.smtp(options, self.loop)

        server_coro = asyncio.start_server(smtp_cap.handle_session, '0.0.0.0', 8888, loop=self.loop)
        self.server = self.loop.run_until_complete(server_coro)

        smtp_task = self.loop.run_in_executor(None, smtp_auth_plain_reject)
        self.loop.run_until_complete(smtp_task)


    def test_AUTH_LOGIN_reject(self):
        """ Makes sure the server rejects all invalid login attempts that use the LOGIN Authentication method.
        """
        def smtp_auth_login_reject():
            smtp_ = smtplib.SMTP('127.0.0.1', 8888, local_hostname='localhost', timeout=15)
            smtp_.docmd('AUTH', 'LOGIN')
            smtp_.docmd(str(base64.b64encode(b'test'), 'utf-8'))
            code, _ = smtp_.docmd(str(base64.b64encode(b'test'), 'utf-8'))
            smtp_.quit()
            self.assertEqual(code, 535)

        options = {'enabled': 'True', 'port': 0, 'protocol_specific_data': {'banner': 'Test'},
                   'users': {'someguy': 'test'}}

        smtp_cap = smtp.smtp(options, self.loop)

        server_coro = asyncio.start_server(smtp_cap.handle_session, '0.0.0.0', 8888, loop=self.loop)
        self.server = self.loop.run_until_complete(server_coro)

        smtp_task = self.loop.run_in_executor(None, smtp_auth_login_reject)
        self.loop.run_until_complete(smtp_task)


if __name__ == '__main__':
    unittest.main()
