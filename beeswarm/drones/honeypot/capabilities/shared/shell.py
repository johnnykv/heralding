# pylint: disable-msg=E1101
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

import argparse
import os
import logging
import sys
import socket
import traceback
from datetime import timedelta

import gevent
from gevent.util import wrap_errors
from fs.errors import ResourceNotFoundError
from fs.path import dirname
from fs.utils import isdir
from telnetsrv.green import TelnetHandler
from telnetsrv.telnetsrvlib import TelnetHandlerBase
from telnetsrv.telnetsrvlib import command

from beeswarm.drones.honeypot.helpers.common import path_to_ls


logger = logging.getLogger(__name__)


class OwnGreenTelnetHandler(TelnetHandler):
    def setup(self):
        TelnetHandlerBase.setup(self)
        # Spawn a greenlet to handle socket input
        self.greenlet_ic = gevent.spawn(wrap_errors((socket.error), self.inputcooker))
        # Note that inputcooker exits on EOF

        # Sleep for 0.5 second to allow options negotiation
        gevent.sleep(0.5)


class Commands(OwnGreenTelnetHandler):
    """This class implements the shell functionality for the telnet and SSH capabilities"""

    max_tries = 3
    PROMPT = ''
    WELCOME = ''
    HOSTNAME = 'host'
    TERM = 'ansi'

    ENVIRONMENT_VARS = {
        'http_proxy': 'http://10.1.0.23/',
        'https_proxy': 'http://10.1.0.23/',
        'ftp_proxy': 'http://10.1.0.23/',
        'BROWSER': 'firefox',
        'EDITOR': 'gedit',
        'SHELL': '/bin/bash',
        'PAGER': 'less'
    }

    authNeedUser = True
    authNeedPass = True

    def __init__(self, request, client_address, server, vfs, session):
        self.vfs = vfs
        self.session = session
        with self.vfs.open('/etc/motd') as motd:
            Commands.WELCOME = motd.read()
        self.working_dir = '/'

        self.total_file_size = 0
        self.update_total_file_size(self.working_dir)

        TelnetHandler.__init__(self, request, client_address, server)

    @command('ls')
    def command_ls(self, params):
        if '-l' in params:
            self.writeline('total ' + str(self.total_file_size))  # report a fake random file size
            file_names = self.vfs.listdir(self.working_dir)
            for fname in file_names:
                abspath = self.vfs.getsyspath(self.working_dir + '/' + fname)
                self.writeline(path_to_ls(abspath))
        else:
            listing = []
            for item in self.vfs.listdir(self.working_dir):
                if isdir(self.vfs, os.path.join(self.working_dir, item)):
                    item += '/'  # Append a slash at the end of directory names
                listing.append(item)
            self.writeline(' '.join(listing))

    @command('echo')
    def command_echo(self, params):
        if not params:
            self.writeline('')
            return
        elif params[0].startswith('$') and len(params) == 1:
            var_name = params[0][1:]
            value = self.ENVIRONMENT_VARS[var_name]
            self.writeline(value)
        elif '*' in params:
            params.remove('*')
            params.extend(self.vfs.listdir())
        else:
            self.writeline(' '.join(params))

    @command('cd')
    def command_cd(self, params):
        if '.' in params:
            return
        newdir = self.working_dir[:]
        if len(params) > 1:
            self.writeline('cd: string not in pwd: {0}'.format(' '.join(params)))
            return
        if len(params) > 0:
            arg = params[0]
            # TODO: Not too sure about what's going on here, need to investigate.
            while arg.startswith('../') or arg == '..':
                if newdir.endswith('/'):
                    newdir = newdir[:-1]
                newdir = dirname(newdir)
                arg = arg[3:]
            newdir = os.path.join(newdir, arg)
        else:
            newdir = os.path.join(newdir, '/')

        try:
            if self.vfs.isdir(newdir):
                self.working_dir = newdir[:]
                self.PROMPT = '[{0}@{1} {2}]$ '.format(self.username, self.HOSTNAME, self.working_dir)
            else:
                self.writeline('cd: no such file or directory: {0}'.format(params[0]))
        except ValueError:
            # Attacker tried to leave the Virtual File system. We wont let him.
            self.working_dir = '/'
            self.PROMPT = '[{0}@{1} {2}]$ '.format(self.username, self.HOSTNAME, self.working_dir)
        self.update_total_file_size(self.working_dir)

    @command('pwd')
    def command_pwd(self, params):
        if params:
            self.writeline('pwd too many arguments')
        self.writeline(self.working_dir)

    @command('uname')
    def command_uname(self, params):

        if not params:
            self.writeline('Linux')
            return

        buff = ''
        info = list(os.uname())
        parser = argparse.ArgumentParser()
        parser.add_argument('-a', '--all', action='store_true', default=False)
        parser.add_argument('-s', '--kernel-name', action='store_true', default=False)
        parser.add_argument('-n', '--nodename', action='store_true', default=False)
        parser.add_argument('-r', '--kernel-release', action='store_true', default=False)
        parser.add_argument('-v', '--kernel-version', action='store_true', default=False)
        parser.add_argument('-m', '--kernel-machine', action='store_true', default=False)
        parser.add_argument('-p', '--processor', action='store_true', default=False)
        parser.add_argument('-i', '--hardware-platform', action='store_true', default=False)
        parser.add_argument('-o', '--operating-system', action='store_true', default=False)

        args = parser.parse_args(params)

        if args.all:
            info.extend(['i686', 'i686', 'GNU/Linux'])
            buff = ' '.join(info)
            self.writeline(buff)
            return
        if args.kernel_name:
            buff = buff + info[0] + ' '
        if args.nodename:
            buff = buff + info[1] + ' '
        if args.kernel_release:
            buff = buff + info[2] + ' '
        if args.kernel_version:
            buff = buff + info[3] + ' '
        if args.kernel_machine:
            buff = buff + info[4] + ' '
        if args.processor:
            buff = buff + info[4] + ' '
        if args.hardware_platform:
            buff = buff + info[4] + ' '
        if args.operating_system:
            buff += 'GNU/Linux'

        self.writeline(buff)

    @command('cat')
    def command_cat(self, params):
        for filename in params:
            filepath = os.path.join(self.working_dir, filename)
            try:
                with self.vfs.open(filepath) as _file:
                    while True:
                        chunk = _file.read(65536)
                        if not chunk:
                            break
                        self.write(chunk)
            except ResourceNotFoundError:
                self.writeline('cat: {0}: No such file or directory'.format(filepath))

    @command('sudo')
    def command_sudo(self, params):
        executable = params[0]
        self.writeline('Sorry, user {} is not allowed to execute \'{}\' as root on {}.'.format(self.username,
                                                                                               executable,
                                                                                               self.HOSTNAME))

    @command('uptime')
    def command_uptime(self, params):
        if '-V' in params:
            self.writeline('procps version 3.2.8')
            return
        with self.vfs.open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            uptime_string = str(timedelta(seconds=uptime_seconds))
        self.writeline(uptime_string)

    def update_total_file_size(self, path):
        size = 0
        for _, info in self.vfs.ilistdirinfo(path):
            size += info['st_blocks']
        self.total_file_size = size

    def handle(self):
        "The actual service to which the user has connected."
        if not self.authentication_ok():
            return
        if self.DOECHO:
            self.writeline(self.WELCOME)
        self.session_start()
        while self.RUNSHELL:
            read_line = self.readline(prompt=self.PROMPT).strip()
            self.session.transcript_incoming(read_line + '\n')
            self.input = self.input_reader(self, read_line)
            self.raw_input = self.input.raw
            if self.input.cmd:
                # TODO: Command should not be converted to upper
                # looks funny in error messages.
                cmd = self.input.cmd.upper()
                params = self.input.params
                if cmd in self.COMMANDS:
                    try:
                        self.COMMANDS[cmd](params)
                    except:
                        logger.exception('Error calling {0}.'.format(cmd))
                        (t, p, tb) = sys.exc_info()
                        if self.handleException(t, p, tb):
                            break
                else:
                    self.writeline('-bash: {0}: command not found'.format(cmd))
                    logger.error("Unknown command '{0}'".format(cmd))
        logger.debug("Exiting handler")

    def handleException(self, exc_type, exc_param, exc_tb):
        logger.warning('Exception during telnet sessions: {0}'.format(''.join(traceback.format_exception(exc_type, exc_param, exc_tb) )))
        return True
