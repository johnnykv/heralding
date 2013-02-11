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

import socket

from handlerbase import HandlerBase
from hive.models.session import Session

import logging

logger = logging.getLogger(__name__)


class pop3(HandlerBase):
    port = 2100
    max_tries = 10
    #port = 110
    cmds = {}

    def __init__(self, sessions):
        self.sessions = sessions

    def handle(self, gsocket, address):
        logger.info("Accepted connection from {0}".format(address))
        state = 'AUTHORIZATION'

        session = Session(address[0], address[1], 'pop3', pop3.port)
        self.sessions[session.id] = session
        session.vdata['MAILSPOOL'] = {}
        session.vdata['deleted_index'] = []

        #just because of readline... tsk tsk...
        fileobj = gsocket.makefile()

        self.send_message(session, gsocket, '+OK POP3 server ready')

        while state != '' and session.is_connected:
            try:
                raw_msg = fileobj.readline()
            except socket.error, (value, message):
                session.is_connected = False
                break

            session.activity()

            msg = None

            if ' ' in raw_msg:
                cmd, msg = raw_msg.rstrip().split(' ', 1)
            else:
                cmd = raw_msg.rstrip()
            cmd = cmd.lower()

            func_to_call = getattr(self, 'cmd_%s' % cmd, None)
            if func_to_call is None or not self.is_state_valid(state, cmd):
                self.send_message(session, gsocket, '-ERR Unknown command')
            else:
                return_value = func_to_call(session, gsocket, msg)
                #state changers!
                if state == 'AUTHORIZATION' or cmd == 'quit':
                    state = return_value

        session.is_connected = False

    #APOP mrose c4c9334bac560ecc979e58001b3e22fb
    #+OK mrose's maildrop has 2 messages (320 octets)
    def auth_apop(self, session, gsocket, msg):
        raise Exception('Not implemented yet!')

    #USER mrose
    #+OK User accepted
    #PASS tanstaaf
    #+OK Pass accepted
    #or: "-ERR Authentication failed."
    #or: "-ERR No username given."
    def cmd_user(self, session, gsocket, msg):
        session.vdata['USER'] = msg
        self.send_message(session, gsocket, '+OK User accepted')
        return 'AUTHORIZATION'.format(msg)

    def is_state_valid(self, state, cmd):
        if state == 'AUTHORIZATION':
            if cmd in ['apop', 'user', 'pass', 'quit']:
                return True;
        elif state == 'TRANSACTION':
            if cmd in ['list', 'retr', 'dele', 'noop', 'stat', 'rset', 'quit']:
                return True
        return False

    def cmd_pass(self, session, gsocket, msg):
        if 'USER' not in session.vdata:
            self.send_message(session, gsocket, '-ERR No username given.')
        else:
            if session.try_login(session.vdata['USER'], msg):
                self.send_message(session, gsocket, "+OK Pass accepted")
                return 'TRANSACTION'

        self.send_message(session, gsocket, "-ERR Authentication failed.")
        if 'USER' in session.vdata:
            del session.vdata['USER']
        return 'AUTHORIZATION'

    def cmd_noop(self, session, gsocket, msg):
        self.send_message(session, gsocket, '+OK')

    def cmd_retr(self, session, gsocket, msg):

        user_mailspool = self.mailspools[session['USER']]

        try:
            index = int(msg) - 1
        except ValueError:
            self.send_message(session, gsocket, '-ERR no such message')
        else:
            if index < 0 or len(user_mailspool) < index:
                self.send_message(session, gsocket, '-ERR no such message')
            else:
                msg = '+OK %i octets' % (len(user_mailspool[index]))
                self.send_message(session, gsocket, msg)
                self.send_data(session, gsocket, user_mailspool[index])
                self.send_message(session, gsocket, '')
                self.send_message(session, gsocket, '.')

    def cmd_dele(self, session, gsocket, msg):

        user_mailspool = session.vdata['MAILSPOOL']

        try:
            index = int(msg) - 1
        except ValueError:
            self.send_message(session, gsocket, '-ERR no such message')
        else:
            if index < 0 or len(user_mailspool) <= index:
                self.send_message(session, gsocket, '-ERR no such message')
            else:
                if index in session['deleted_index']:
                    reply = '-ERR message %s already deleted' % (msg)
                    self.send_message(session, gsocket, reply)
                else:
                    session['deleted_index'].append(index)
                    reply = '+OK message %s deleted' % (msg)
                    self.send_message(session, gsocket, reply)


    def cmd_stat(self, session, gsocket, msg):

        user_mailspool = session.vdata['MAILSPOOL']
        mailspool_bytes_size = 0
        mailspool_num_messages = 0

        for index, value in enumerate(user_mailspool):
            if index not in session.vdata['deleted_index']: # ignore deleted messages
                mailspool_bytes_size += len(value)
                mailspool_num_messages += 1

        reply = '+OK %i %i' % (mailspool_num_messages, mailspool_bytes_size)

        self.send_message(session, gsocket, reply)


    def cmd_quit(self, session, gsocket, msg):
        self.send_message(session, gsocket, '+OK Logging out')

        user_mailspool = session.vdata['MAILSPOOL']

        #session['deleted_index'].sort(reverse=True)
        #for index in session['deleted_index']:
        #    del user_mailspool[index]
        return ''

    def cmd_list(self, session, gsocket, argument):
        user_mailspool = session.vdata['MAILSPOOL']

        if argument is None:
            mailspool_bytes_size = 0
            mailspool_num_messages = 0

            for index, value in enumerate(user_mailspool):
                if index not in session['deleted_index']: # ignore deleted messages
                    mailspool_bytes_size += len(value)
                    mailspool_num_messages += 1

            reply = "+OK %i messages (%i octets)" % (mailspool_num_messages, mailspool_bytes_size)
            self.send_message(session, gsocket, reply)

            for index, value in enumerate(user_mailspool):
                if index not in session['deleted_index']: # ignore deleted messages
                    reply = "%i %i" % (index + 1, len(value))
                    self.send_message(session, gsocket, reply)
            self.send_message(session, gsocket, '.')
        else:
            index = int(argument) - 1
            if index < 0 or len(user_mailspool) <= index or index in session['deleted_index']:
                reply = '-ERR no such message'
                self.send_message(session, gsocket, reply)
            else:
                mail = user_mailspool[index]
                reply = '+OK %i %i' % (index + 1, len(mail))
                self.send_message(session, gsocket, reply)

    def get_port(self):
        return pop3.port

    def not_impl(self, session, gsocket, msg):
        raise Exception('Not implemented yet!')

    def send_message(self, session, gsocket, msg):
        try:
            gsocket.sendall(msg + "\n")
        except socket.error, (value, msg):
            session.is_connected = False

    def send_data(self, session, gsocket, data):
        try:
            gsocket.sendall(data)
        except socket.error, (value, msg):
            session.is_connected = False

