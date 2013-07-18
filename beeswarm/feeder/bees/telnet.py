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
import telnetlib
import re

from beeswarm.feeder.bees.clientbase import ClientBase


class telnet(ClientBase):

    def __init__(self, sessions, options):
        super(telnet, self).__init__(sessions, options)
        self.client = None
        self.state = {
            'last_command': None,
            'working_dir': '/',
            'file_list': [],
        }
        self.senses = [self.pwd, self.uname, self.uptime, self.list]
        self.actions = [self.change_dir, self.cat, self.echo, self.sudo]

    def connect(self):
        self.client = telnetlib.Telnet(self.options['server'], self.options['port'])
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
            self.list('-l')
            logging.debug('Telnet file listing successful.')
            self.client.write('exit\r\n')
            self.client.read_all()
            self.client.close()
        finally:
            session.alldone = True

    def change_dir(self, params=''):
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
        cmd = 'cd {}'.format(params)
        self.send_command(cmd)
        return self.get_response()

    def sudo(self, params=''):
        cmd = 'cd {}'.format(params)
        self.send_command(cmd)
        return self.get_response()

    def list(self, params=''):
        cmd = 'ls {}'.format(params)
        self.send_command(cmd)
        resp_raw = self.get_response()
        resp = resp_raw.split('\r\n')
        if params:
            # Our Hive capability only accepts "ls -l" or "ls" so params will always be "-l"
            files = []
            for line in resp[2:-1]:  # Discard the line with echoed command, total and prompt
                # 8 Makes sure we have the right result even if filenames have spaces.
                filename = line.split(' ', 8)[-1]
                files.append(filename)
            self.state['file_list'] = files
        else:
            resp = '\r\n'.join(resp[1:-1])
            self.state['file_list'] = resp.split()
        return resp_raw

    def get_response(self):
        response = self.client.read_until('$ ', 5)
        return response

    def send_command(self, cmd):
        self.client.write(cmd + '\r\n')
        self.state['last_command'] = cmd

    def process_options(self, *args):
        """Dummy callback, used to disable options negotiations"""


class InvalidLogin(Exception):
    pass