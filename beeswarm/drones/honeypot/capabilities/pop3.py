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
import logging

from beeswarm.drones.honeypot.capabilities.handlerbase import HandlerBase


logger = logging.getLogger(__name__)


class Pop3(HandlerBase):
    max_tries = 10
    cmds = {}

    def __init__(self, sessions, options, workdir):
        super(Pop3, self).__init__(sessions, options, workdir)
        Pop3.max_tries = int(self.options['protocol_specific_data']['max_attempts'])

    def handle_session(self, gsocket, address):
        session = self.create_session(address, gsocket)

        session.vdata['MAILSPOOL'] = {}
        session.vdata['deleted_index'] = []

        fileobj = gsocket.makefile()

        self.send_message(session, gsocket, '+OK POP3 server ready')

        state = 'AUTHORIZATION'
        while state != '' and session.connected:
            try:
                raw_msg = fileobj.readline()
            except socket.error:
                session.connected = False
                break

            session.activity()
            session.transcript_incoming(raw_msg)
            cmd_msg = raw_msg.rstrip().split(' ', 1)
            if len(cmd_msg) == 0:
                continue
            elif len(cmd_msg) == 1:
                cmd = cmd_msg[0]
                msg = ''
            else:
                cmd = cmd_msg[0]
                msg = cmd_msg[1]

            cmd = cmd.lower()

            func_to_call = getattr(self, 'cmd_%s' % cmd, None)
            if func_to_call is None or not self.is_state_valid(state, cmd):
                self.send_message(session, gsocket, '-ERR Unknown command')
            else:
                return_value = func_to_call(session, gsocket, msg)
                # state changers!
                if state == 'AUTHORIZATION' or cmd == 'quit':
                    state = return_value

        session.connected = False

    # APOP mrose c4c9334bac560ecc979e58001b3e22fb
    # +OK mrose's maildrop has 2 messages (320 octets)
    def auth_apop(self, session, gsocket, msg):
        raise Exception('Not implemented yet!')

    # USER mrose
    # +OK User accepted
    # PASS tanstaaf
    # +OK Pass accepted
    # or: "-ERR Authentication failed."
    # or: "-ERR No username given."
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
            if session.try_auth('plaintext', username=session.vdata['USER'], password=msg):
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
            if index not in session.vdata['deleted_index']:  # ignore deleted messages
                mailspool_bytes_size += len(value)
                mailspool_num_messages += 1

        reply = '+OK %i %i' % (mailspool_num_messages, mailspool_bytes_size)

        self.send_message(session, gsocket, reply)

    def cmd_quit(self, session, gsocket, msg):
        self.send_message(session, gsocket, '+OK Logging out')

        user_mailspool = session.vdata['MAILSPOOL']

        # session['deleted_index'].sort(reverse=True)
        # for index in session['deleted_index']:
        # del user_mailspool[index]
        return ''

    def cmd_list(self, session, gsocket, argument):
        user_mailspool = session.vdata['MAILSPOOL']

        if not argument:
            mailspool_bytes_size = 0
            mailspool_num_messages = 0

            for index, value in enumerate(user_mailspool):
                if index not in session['deleted_index']:  # ignore deleted messages
                    mailspool_bytes_size += len(value)
                    mailspool_num_messages += 1

            reply = "+OK %i messages (%i octets)" % (mailspool_num_messages, mailspool_bytes_size)
            self.send_message(session, gsocket, reply)

            for index, value in enumerate(user_mailspool):
                if index not in session['deleted_index']:  # ignore deleted messages
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

    def not_impl(self, session, gsocket, msg):
        raise Exception('Not implemented yet!')

    def send_message(self, session, gsocket, msg):
        try:
            session.transcript_outgoing(msg + '\n')
            gsocket.sendall(msg + "\n")
        except socket.error, (value, msg):
            session.connected = False

    def send_data(self, session, gsocket, data):
        try:
            gsocket.sendall(data)
        except socket.error, (value, msg):
            session.connected = False

