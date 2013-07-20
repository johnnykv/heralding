# Copyright (C) 2013 Aniket Panse <contact@aniketpanse.in>
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

import logging
import random
import string
import telnetlib
import re
import time

from beeswarm.feeder.bees.clientbase import ClientBase


class BeeTelnetClient(telnetlib.Telnet):

    IAC = chr(255)

    def write_human(self, buffer_):
        if self.IAC in buffer_:
            buffer_ = buffer_.replace(self.IAC, self.IAC+self.IAC)
        self.msg("send %r", buffer_)
        for char in buffer_:
            delta = random.gauss(80, 20)
            self.sock.sendall(char)
            time.sleep(delta/1000.0)  # Convert milliseconds to seconds


class telnet(ClientBase):

    COMMAND_MAP = {
        'pwd': ['ls', 'uname', 'uptime'],
        'cd': ['ls'],
        'uname': ['uptime', 'ls'],
        'ls': ['cd', 'cat', 'pwd'],
        'cat': ['ls', 'echo', 'sudo', 'pwd'],
        'uptime': ['ls', 'echo', 'sudo', 'uname', 'pwd'],
        'echo': ['ls', 'echo', 'sudo', 'uname', 'pwd'],
        'sudo': ['logout']
    }

    def __init__(self, sessions, options):
        super(telnet, self).__init__(sessions, options)
        self.client = None
        self.state = {
            # Hack! Assume that the client has initially performed an echo to avoid KeyErrors
            'last_command': 'echo',
            'working_dir': '/',
            'file_list': [],
            'dir_list': [],
        }
        self.command_count = 0
        self.command_limit = random.randint(6, 11)
        self.senses = ['pwd', 'uname', 'uptime', 'ls']
        self.actions = ['cd', 'cat', 'echo', 'sudo']

    def connect(self):
        self.client = BeeTelnetClient(self.options['server'], self.options['port'])
        self.client.set_option_negotiation_callback(self.process_options)

    def login(self, login, password):
        self.client.read_until('Username: ')
        self.client.write(login + '\r\n')
        self.client.read_until('Password: ')
        self.client.write(password + '\r\n')
        current_data = self.client.read_until('$ ', 5)
        if not current_data.endswith('$ '):
            raise InvalidLogin

    def do_session(self, my_ip):
        login = self.options['login']
        password = self.options['password']
        server_host = self.options['server']
        server_port = self.options['port']
        session = self.create_session(login, password, server_host, server_port, my_ip)
        self.sessions[session.id] = session
        logging.debug(
            'Sending %s honeybee to %s:%s. (bee id: %s)' % ('telnet', server_host, server_port, session.id))

        try:
            self.connect()
            self.login(login, password)
            session.did_connect = True
            session.source_port = self.client.sock.getsockname()[1]
            session.did_login = True
        except Exception as err:
            logging.debug('Caught exception: %s (%s)' % (err, str(type(err))))
        else:
            while self.command_count < self.command_limit:
                self.sense()
                comm, param = self.decide()
                self.act(comm, param)
                time.sleep(10)
        finally:
            session.alldone = True

    def logout(self):
        self.client.write('exit\r\n')
        self.client.read_all()
        self.client.close()

    def cd(self, params=''):
        cmd = 'cd {}'.format(params)
        self.send_command(cmd)
        data = self.get_response()
        prompt = data.rsplit('\r\n', 1)[1]
        pattern = re.compile(r'/[/\w]+')
        self.state['working_dir'] = pattern.findall(prompt)[0]
        return data

    def pwd(self, params=''):
        cmd = 'pwd {}'.format(params)
        self.send_command(cmd)
        return self.get_response()

    def uname(self, params=''):
        cmd = 'uname {}'.format(params)
        self.send_command(cmd)
        return self.get_response()

    def cat(self, params=''):
        cmd = 'cat {}'.format(params)
        self.send_command(cmd)
        return self.get_response()

    def uptime(self, params=''):
        cmd = 'uptime {}'.format(params)
        self.send_command(cmd)
        return self.get_response()

    def echo(self, params=''):
        cmd = 'echo {}'.format(params)
        self.send_command(cmd)
        return self.get_response()

    def sudo(self, params=''):
        cmd = 'sudo {}'.format(params)
        self.send_command(cmd)
        return self.get_response()

    def ls(self, params=''):
        cmd = 'ls {}'.format(params)
        self.send_command(cmd)
        resp_raw = self.get_response()
        resp = resp_raw.split('\r\n')
        files = []
        dirs = []
        if params:
            # Our Hive capability only accepts "ls -l" or "ls" so params will always be "-l"
            for line in resp[2:-1]:  # Discard the line with echoed command, total and prompt
                # 8 Makes sure we have the right result even if filenames have spaces.
                info = line.split(' ', 8)
                name = info[-1]
                if info[0].startswith('d'):
                    dirs.append(name)
                else:
                    files.append(name)
        else:
            resp = '\r\n'.join(resp[1:-1])
            names = resp.split()
            for name in names:
                if name.endswith('/'):
                    dirs.append(name)
                else:
                    files.append(name)
        self.state['file_list'] = files
        self.state['dir_list'] = dirs
        return resp_raw

    def sense(self):
        cmd_name = random.choice(self.senses)
        param = ''
        if cmd_name == 'ls':
            if random.randint(0, 1):
                param = '-l'
        elif cmd_name == 'uname':
            # Choose options from predefined ones
            opts = 'asnrvmpio'
            start = random.randint(0, len(opts)-2)
            end = random.randint(start+1, len(opts)-1)
            param = '-{}'.format(opts[start:end])
        command = getattr(self, cmd_name)
        self.command_count += 1
        command(param)

    def decide(self):

        next_command_name = random.choice(self.COMMAND_MAP[self.state['last_command']])
        param = ''
        if next_command_name == 'cd':
            try:
                param = random.choice(self.state['dir_list'])
            except IndexError:
                next_command_name = 'ls'

        elif next_command_name == 'uname':
            opts = 'asnrvmpio'
            start = random.randint(0, len(opts)-2)
            end = random.randint(start+1, len(opts)-1)
            param = '-{}'.format(opts[start:end])
        elif next_command_name == 'ls':
            if random.randint(0, 1):
                param = '-l'
        elif next_command_name == 'cat':
            try:
                param = random.choice(self.state['file_list'])
            except IndexError:
                param = ''.join(random.choice(string.lowercase) for x in range(3))
        elif next_command_name == 'echo':
            param = random.choice([
                'yay we rock!',
                'test',
                'looks like ssh\'s working fine'
            ])
        elif next_command_name == 'sudo':
            param = random.choice([
                'pm-hibernate',
                'shutdown -h',
                'vim /etc/httpd.conf',
                'vim /etc/resolve.conf',
                'service network restart',
                '/etc/init.d/network-manager restart',
            ])
        return next_command_name, param

    def act(self, cmd_name, params):
        command = getattr(self, cmd_name)
        command(params)

    def get_response(self):
        response = self.client.read_until('$ ', 5)
        return response

    def send_command(self, cmd):
        if self.command_count > self.command_limit:
            self.logout()
            return
        logging.debug('Sending %s command.' % cmd)
        self.command_count += 1
        self.client.write_human(cmd + '\r\n')

    def process_options(self, *args):
        """Dummy callback, used to disable options negotiations"""


class InvalidLogin(Exception):
    pass