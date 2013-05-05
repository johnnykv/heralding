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

from gevent.server import StreamServer
import gevent
import unittest
from hive.capabilities import pop3
from hive.models.session import Session
from hive.models.authenticator import Authenticator
from hive.models.user import HiveUser


class Pop3_Tests(unittest.TestCase):

    def test_initial_session(self):
        """Tests if the basic parts of the session is filled correctly"""

        sessions = {}

        #provide valid login/pass to authenticator
        authenticator = Authenticator({'james': 'bond'})
        Session.authenticator = authenticator

        users = {'test': HiveUser('test', 'test')}
        sut = pop3.pop3(sessions, {'port': 110, 'max_attempts': 3}, users)

        #dont really care about the socket at this point (None...)
        #TODO: mock the socket!
        try:
            sut.handle_session(None, ['192.168.1.200', 12000])
        except AttributeError:
            #because socket is not set
            pass

        #expect a single entry in the sessions dict
        self.assertEqual(1, len(sessions))
        session = sessions.values()[0]
        self.assertEqual(110, session.honey_port)
        self.assertEqual('pop3', session.protocol)
        self.assertEquals('192.168.1.200', session.attacker_ip)
        self.assertEqual(12000, session.attacker_source_port)

    def test_login(self):
        """Testing different login combinations"""

        #provide valid login/pass to authenticator
        authenticator = Authenticator({'james': 'bond'})
        Session.authenticator = authenticator

        login_sequences = [
            #valid login. valid password
            (('USER james', '+OK User accepted'), ('PASS bond', '+OK Pass accepted')),
            #valid login, invalid password, try to run TRANSACTION state command
            (('USER james', '+OK User accepted'), ('PASS wakkawakka', '-ERR Authentication failed.'),
             ('RETR', '-ERR Unknown command')),
            #invalid login, invalid password
            (('USER wakkwakk', '+OK User accepted'), ('PASS wakkwakk', '-ERR Authentication failed.')),
            #PASS without user
            (('PASS bond', '-ERR No username given.'),),
            #Try to run a TRANSACITON state command in AUTHORIZATION state
            (('RETR', '-ERR Unknown command'),),
        ]

        sessions = {}

        users = {'test': HiveUser('test', 'test')}
        sut = pop3.pop3(sessions, {'port': 110, 'max_attempts': 3}, users)

        server = StreamServer(('127.0.0.1', 0), sut.handle_session)
        server.start()

        for sequence in login_sequences:
            client = gevent.socket.create_connection(('127.0.0.1', server.server_port))

            fileobj = client.makefile()

            #skip banner
            fileobj.readline()

            for pair in sequence:
                client.sendall(pair[0] + "\r\n")
                response = fileobj.readline().rstrip()
                self.assertEqual(response, pair[1])

        server.stop()

    # def test_dele(self):
    #     """Testing DELE command"""
    #
    #     sequences = [
    #         #[mailspool_initialstate], ((cmd, response), (cmd, response))
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


if __name__ == '__main__':
    unittest.main()