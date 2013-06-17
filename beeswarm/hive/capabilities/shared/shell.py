import argparse
import os
from fs.errors import ResourceNotFoundError
from fs.path import dirname
from telnetsrv.green import TelnetHandler
from telnetsrv.telnetsrvlib import command
from beeswarm.hive.helpers.common import path_to_ls
from datetime import timedelta


class Commands(TelnetHandler):

    """This class implements the shell functionality for the telnet and SSH capabilities"""

    max_tries = 3
    PROMPT = ''

    WELCOME = ''

    HOSTNAME = 'host'
    authNeedUser = True
    authNeedPass = True
    TERM = 'ansi'

    def __init__(self, request, client_address, server, vfs):
        self.vfs = vfs
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
            self.writeline(' '.join(self.vfs.listdir(self.working_dir)))

    @command('echo')
    def command_echo(self, params):
        if not params:
            self.writeline('')
            return
        elif '*' in params:
            params.remove('*')
            params.extend(self.vfs.listdir())
        self.writeline(' '.join(params))

    @command('cd')
    def command_cd(self, params):
        if '.' in params:
            return
        newdir = self.working_dir[:]
        if len(params) > 1:
            self.writeline('cd: string not in pwd: {0}'.format(' '.join(params)))
            return
        arg = params[0]
        while arg.startswith('../') or arg == '..':
            if newdir.endswith('/'):
                newdir = newdir[:-1]
            newdir = dirname(newdir)
            arg = arg[3:]
        newdir = os.path.join(newdir, arg)
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
            pass
        self.update_total_file_size(self.working_dir)

    @command('pwd')
    def command_pwd(self, params):
        self.writeline(self.working_dir)

    @command('uname')
    def command_uname(self, params):
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
                with self.vfs.open(filepath) as f:
                    while True:
                        chunk = f.read(65536)
                        if not chunk:
                            break
                        self.write(chunk)
            except ResourceNotFoundError:
                self.writeline('cat: {0}: No such file or directory'.format(filepath)

    @command('uptime')
    def command_uptime(self, params):
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            uptime_string = str(timedelta(seconds=uptime_seconds))
        self.writeline(uptime_string)

    def update_total_file_size(self, path):
        size = 0
        for dirname, info in self.vfs.ilistdirinfo(path):
            size += info['st_blocks']
        self.total_file_size = size

