# Copyright (C) 2012 Johnny Vestergaard <jkv@unixcluster.dk>
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

import unittest
import shutil
import tempfile
import os

from gevent.server import StreamServer
import gevent

from beeswarm.drones.honeypot.honeypot import Honeypot
from beeswarm.drones.honeypot.capabilities.pop3 import Pop3


class Pop3Tests(unittest.TestCase):
    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        Honeypot.prepare_environment(self.work_dir)

    def tearDown(self):
        if os.path.isdir(self.work_dir):
            shutil.rmtree(self.work_dir)

    def test_initial_session(self):
        """Tests if the basic parts of the session is filled correctly"""

        sessions = {}
        options = {'port': 110, 'protocol_specific_data': {'max_attempts': 3}, 'users': {'test': 'test'}}
        sut = Pop3(sessions, options, self.work_dir)

        # dont really care about the socket at this point (None...)
        # TODO: mock the socket!
        try:
            sut.handle_session(None, ['192.168.1.200', 12000])
        except AttributeError:
            # because socket is not set
            pass

        # expect a single entry in the sessions dict
        self.assertEqual(1, len(sessions))
        session = sessions.values()[0]
        self.assertEqual(110, session.destination_port)
        self.assertEqual('pop3', session.protocol)
        self.assertEquals('192.168.1.200', session.source_ip)
        self.assertEqual(12000, session.source_port)

    def test_login(self):
        """Testing different login combinations"""

        login_sequences = [
            # valid login. valid password
            (('USER james', '+OK User accepted'), ('PASS bond', '+OK Pass accepted')),
            # valid login, invalid password, try to run TRANSACTION state command
            (('USER james', '+OK User accepted'), ('PASS wakkawakka', '-ERR Authentication failed.'),
             ('RETR', '-ERR Unknown command')),
            # invalid login, invalid password
            (('USER wakkwakk', '+OK User accepted'), ('PASS wakkwakk', '-ERR Authentication failed.')),
            #PASS without user
            (('PASS bond', '-ERR No username given.'),),
            #Try to run a TRANSACITON state command in AUTHORIZATION state
            (('RETR', '-ERR Unknown command'),),
        ]

        sessions = {}
        options = {'port': 110, 'protocol_specific_data': {'max_attempts': 3}, 'users': {'james': 'bond'}}
        sut = Pop3(sessions, options, self.work_dir)

        server = StreamServer(('127.0.0.1', 0), sut.handle_session)
        server.start()

        for sequence in login_sequences:
            client = gevent.socket.create_connection(('127.0.0.1', server.server_port))

            fileobj = client.makefile()

            # skip banner
            fileobj.readline()

            for pair in sequence:
                client.sendall(pair[0] + "\r\n")
                response = fileobj.readline().rstrip()
                self.assertEqual(response, pair[1])

        server.stop()

        # def test_dele(self):
        # """Testing DELE command"""
        #
        # sequences = [
        # #[mailspool_initialstate], ((cmd, response), (cmd, response))
        #         #Delete message
        #         (['mail1', 'mail2'], (('DELE 1', '+OK message 1 deleted'), ('STAT', '+OK 1 5'))),
        #         #Delete message twice
        #         (['mail1', 'mail2'], (('DELE 1', '+OK message 1 deleted'), ('STAT', '+OK 1 5'))),
        #         #Delete non-existing mail
        #         (['mail1'], (('DELE 2', '-ERR no such message'),)),
        #     ]
        #
        #     sessions = {}
        #     accounts = {'james': 'bond'}
        #     sut = pop3.pop3(sessions, accounts)
        #
        #     server = StreamServer(('127.0.0.1', 0), sut.handle_session)
        #     server.start()
        #
        #     for sequence in sequences:
        #         client = gevent.socket.create_connection(('127.0.0.1', server.server_port))
        #
        #         fileobj = client.makefile()
        #
        #         #set initial mailstate
        #         sut.mailspools['james'] = sequence[0]
        #
        #         #skip banner and login
        #         fileobj.readline()
        #         client.sendall('USER james' + "\r\n")
        #         fileobj.readline()
        #         client.sendall('PASS bond' + "\r\n")
        #         fileobj.readline()
        #
        #         for pair in sequence[1]:
        #             client.sendall(pair[0] + "\r\n")
        #             response = fileobj.readline().rstrip()
        #             self.assertEqual(response, pair[1])
        #
        #     server.stop()
        #
        # def test_stat(self):
        #     """Testing STAT command"""
        #
        #     sequences = [
        #         #[mailspool_initialstate], ((cmd, response), (cmd, response))
        #         #Delete message
        #         ([], (('STAT', '+OK 0 0'),)),
        #         (['mail1'], (('STAT', '+OK 1 5'),)),
        #         (['mail1', 'mail2'], (('STAT', '+OK 2 10'),)),
        #     ]
        #
        #     sessions = {}
        #     accounts = {'james': 'bond'}
        #     sut = pop3.pop3(sessions, accounts)
        #
        #     server = StreamServer(('127.0.0.1', 0), sut.handle_session)
        #     server.start()
        #
        #     for sequence in sequences:
        #         client = gevent.socket.create_connection(('127.0.0.1', server.server_port))
        #
        #         fileobj = client.makefile()
        #
        #         #set initial mailstate
        #         sut.mailspools['james'] = sequence[0]
        #
        #         #skip banner and login
        #         fileobj.readline()
        #         client.sendall('USER james' + "\r\n")
        #         fileobj.readline()
        #         client.sendall('PASS bond' + "\r\n")
        #         fileobj.readline()
        #
        #         for pair in sequence[1]:
        #             client.sendall(pair[0] + "\r\n")
        #             response = fileobj.readline().rstrip()
        #             self.assertEqual(response, pair[1])
        #
        #     server.stop()
