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

from hive.models.session import Session

from handlerbase import HandlerBase

logger = logging.getLogger(__name__)

class telnet(HandlerBase):
    max_tries = 3

    def __init__(self, sessions):
        self.sessions = sessions

    def handle(self, gsocket, address):
        session = Session(address[0], address[1], 'telnet', telnet.port)
        self.sessions[session.id] = session

        logger.info("Accepted connection from {0}:{1}. ({2})".format(address[0], address[1], session.id))

        banner = ''

        self.send_message(session, gsocket, banner)

        self.send_message(session, gsocket, "Login: ")

        data = []
        state = ''
        prompt = 'login'
        auth_attempts = 0

        while auth_attempts < telnet.max_tries:

            try:
                read = gsocket.recv(1)
            except socket.error, (value, message):
                session.is_connected = False
                break

            session.activity()

            if state == '':
                if read == IAC:
                    data.append(read)
                    state = 'iac'
                #start negotiation (SB)
                elif read == SB:
                    data.append(read)
                    state = 'negotiation'
                else:
                    data.append(read)
                    if len(data) > 1:
                        if data[-1] == '\n' and data[-2] == '\r':
                            if prompt == 'login':
                                login = ''.join(data)[:-2]
                                self.send_message(session, gsocket, "Password: ")
                                data = []
                                #instruct client not to echo
                                self.send_message(session, gsocket, IAC + WILL + ECHO)
                                prompt = 'password'
                            else:
                                password = ''.join(data)[:-2]
                                session.try_login(login, password)
                                auth_attempts += 1

                                self.send_message(session, gsocket, '\r\nInvalid username/password.\r\n')
                                #instruct client to echo again
                                self.send_message(session, gsocket, IAC + WONT + ECHO)
                                prompt = 'login'
                                data = []
                                if auth_attempts < telnet.max_tries:
                                    self.send_message(session, gsocket, "login: ")
            elif state == 'negotiation':
                if read == SE:
                    data.append(read)
                    self.parse_cmd(session, gsocket, data)
                    state = ''
                    data = []
            elif state == 'iac':
                if read in (NOP, DM, BRK, IP, AO, AYT, EC, EL, GA):
                    data.append(read)
                    self.parse_cmd(session, gsocket, data)
                    state = ''
                    data = []
                elif read in (WILL, WONT, DO, DONT):
                    state = 'command'
                    data.append(read)
            elif state == 'command':
                data.append(read)
                self.parse_cmd(session, gsocket, data)
                state = ''
                data = []

        session.is_connected = False

    def parse_cmd(self, session, gsocket, data):
        #TODO: Log comands - these commands can be used to fingerprint attack tool.
        command = data

    def send_message(self, session, gsocket, msg):
        try:
            gsocket.sendall(msg)
        except socket.error, (value, msg):
            session['is_connected'] = False


#telnet commands accordingly to various RFC (857-860, 1091, 1073, 1079, 1372, 1184, 1408)
ECHO = chr(1)
SUPPRESS_GO_AHEAD = chr(3)
STATUS = chr(5)
TIMING_MARK = chr(6)
TERMINAL_TYPE = chr(24)
WINDOW_SIZE = chr(31)
TERMINAL_SPEED = chr(32)
REMOTE_FLOW_CONTROL = chr(33)
LINEMODE = chr(34)
ENVIRONMENT_VARIABLES = chr(36)

#End of subnegotiation parameters
SE = chr(240)
#No operation
NOP = chr(241)
#Data mark
DM = chr(242)
#Suspend
BRK = chr(243)
#Suspend
IP = chr(244)
#Abort output
AO = chr(245)
#Are you there
AYT = chr(246)
#Erase character
EC = chr(247)
#Erase line
EL = chr(248)
#Go ahead
GA = chr(249)
#Start of subnegotiation
SB = chr(250)
WILL = chr(251)
WONT = chr(252)
DO = chr(253)
DONT = chr(254)
#Interpret as a command
IAC = chr(255)

