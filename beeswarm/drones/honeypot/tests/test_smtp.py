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

import smtplib
import base64
import hmac
import os
import tempfile
import shutil

import gevent.monkey
from gevent.server import StreamServer

from beeswarm.drones.honeypot.honeypot import Honeypot
from beeswarm.drones.honeypot.capabilities import smtp


gevent.monkey.patch_all()

import unittest


class SmtpTests(unittest.TestCase):
    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        Honeypot.prepare_environment(self.work_dir)

    def tearDown(self):
        if os.path.isdir(self.work_dir):
            shutil.rmtree(self.work_dir)

    def test_connection(self):
        """ Tries to connect and run a EHLO command. Very basic test.
        """

        sessions = {}
        # Use uncommon port so that we can run test even if the Honeypot is running.
        options = {'enabled': 'True', 'port': 0, 'protocol_specific_data': {'banner': 'test'},
                   'users': {'test': 'test'}, }
        cap = smtp.smtp(sessions, options, self.work_dir)
        srv = StreamServer(('0.0.0.0', 0), cap.handle_session)
        srv.start()

        smtp_ = smtplib.SMTP('127.0.0.1', srv.server_port, local_hostname='localhost', timeout=15)
        smtp_.ehlo()
        smtp_.quit()
        srv.stop()

    def test_AUTH_CRAM_MD5_reject(self):
        """ Makes sure the server rejects all invalid login attempts that use the
            CRAM-MD5 Authentication method.
        """

        sessions = {}

        options = {'enabled': 'True', 'port': 0, 'protocol_specific_data': {'banner': 'Test'},
                   'users': {'someguy': 'test'}}
        cap = smtp.smtp(sessions, options, self.work_dir)
        srv = StreamServer(('0.0.0.0', 0), cap.handle_session)
        srv.start()

        def encode_cram_md5(challenge, user, password):
            challenge = base64.decodestring(challenge)
            response = user + ' ' + hmac.HMAC(password, challenge).hexdigest()
            return base64.b64encode(response)

        smtp_ = smtplib.SMTP('127.0.0.1', srv.server_port, local_hostname='localhost', timeout=15)
        _, resp = smtp_.docmd('AUTH', 'CRAM-MD5')
        code, resp = smtp_.docmd(encode_cram_md5(resp, 'test', 'test'))
        # For now, the server's going to return a 535 code.
        self.assertEqual(code, 535)
        srv.stop()

    def test_AUTH_PLAIN_reject(self):
        """ Makes sure the server rejects all invalid login attempts that use the PLAIN Authentication method.
        """
        sessions = {}
        options = {'enabled': 'True', 'port': 0, 'protocol_specific_data': {'banner': 'Test'},
                   'users': {'someguy': 'test'}}

        cap = smtp.smtp(sessions, options, self.work_dir)
        srv = StreamServer(('0.0.0.0', 0), cap.handle_session)
        srv.start()

        smtp_ = smtplib.SMTP('127.0.0.1', srv.server_port, local_hostname='localhost', timeout=15)
        arg = '\0%s\0%s' % ('test', 'test')
        code, resp = smtp_.docmd('AUTH', 'PLAIN ' + base64.b64encode(arg))
        self.assertEqual(code, 535)
        srv.stop()

    def test_AUTH_LOGIN_reject(self):
        """ Makes sure the server rejects all invalid login attempts that use the LOGIN Authentication method.
        """

        sessions = {}
        options = {'enabled': 'True', 'port': 0, 'protocol_specific_data': {'banner': 'Test'},
                   'users': {'someguy': 'test'}}

        cap = smtp.smtp(sessions, options, self.work_dir)
        srv = StreamServer(('0.0.0.0', 0), cap.handle_session)
        srv.start()

        smtp_ = smtplib.SMTP('127.0.0.1', srv.server_port, local_hostname='localhost', timeout=15)
        smtp_.docmd('AUTH', 'LOGIN')
        smtp_.docmd(base64.b64encode('test'))
        code, resp = smtp_.docmd(base64.b64encode('test'))
        self.assertEqual(code, 535)
        srv.stop()

    def test_AUTH_CRAM_MD5(self):
        """ Makes sure the server accepts valid login attempts that use the CRAM-MD5 Authentication method.
        """

        sessions = {}

        options = {'enabled': 'True', 'port': 0, 'protocol_specific_data': {'banner': 'Test'},
                   'users': {'test': 'test'}}

        cap = smtp.smtp(sessions, options, self.work_dir)
        srv = StreamServer(('0.0.0.0', 0), cap.handle_session)
        srv.start()

        def encode_cram_md5(challenge, user, password):
            challenge = base64.decodestring(challenge)
            response = user + ' ' + hmac.HMAC(password, challenge).hexdigest()
            return base64.b64encode(response)

        smtp_ = smtplib.SMTP('127.0.0.1', srv.server_port, local_hostname='localhost', timeout=15)
        _, resp = smtp_.docmd('AUTH', 'CRAM-MD5')
        code, resp = smtp_.docmd(encode_cram_md5(resp, 'test', 'test'))
        # For now, the server's going to return a 535 code.
        self.assertEqual(code, 235)
        srv.stop()

    def test_AUTH_PLAIN(self):
        """ Makes sure the server accepts valid login attempts that use the PLAIN Authentication method.
        """

        sessions = {}
        options = {'enabled': 'True', 'port': 0, 'protocol_specific_data': {'banner': 'Test'},
                   'users': {'test': 'test'}}

        cap = smtp.smtp(sessions, options, self.work_dir)
        srv = StreamServer(('0.0.0.0', 0), cap.handle_session)
        srv.start()

        smtp_ = smtplib.SMTP('127.0.0.1', srv.server_port, local_hostname='localhost', timeout=15)
        arg = '\0%s\0%s' % ('test', 'test')
        code, resp = smtp_.docmd('AUTH', 'PLAIN ' + base64.b64encode(arg))
        self.assertEqual(code, 235)
        srv.stop()

    def test_AUTH_LOGIN(self):
        """ Makes sure the server accepts valid login attempts that use the LOGIN Authentication method.
        """

        sessions = {}
        options = {'enabled': 'True', 'port': 0, 'protocol_specific_data': {'banner': 'Test'},
                   'users': {'test': 'test'}}

        cap = smtp.smtp(sessions, options, self.work_dir)
        srv = StreamServer(('0.0.0.0', 0), cap.handle_session)
        srv.start()

        smtp_ = smtplib.SMTP('127.0.0.1', srv.server_port, local_hostname='localhost', timeout=15)
        smtp_.docmd('AUTH', 'LOGIN')
        smtp_.docmd(base64.b64encode('test'))
        code, resp = smtp_.docmd(base64.b64encode('test'))
        self.assertEqual(code, 235)
        srv.stop()


if __name__ == '__main__':
    unittest.main()
