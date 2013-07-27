import re


class Commands(object):

    COMMAND_MAP = {
        'pwd': ['ls', 'uname', 'uptime'],
        'cd': ['ls'],
        'uname': ['uptime', 'ls'],
        'ls': ['cd', 'cat', 'pwd'],
        'cat': ['ls', 'echo', 'sudo', 'pwd'],
        'uptime': ['ls', 'echo', 'sudo', 'uname', 'pwd'],
        'echo': ['ls', 'sudo', 'uname', 'pwd'],
        'sudo': ['logout']
    }

    def __init__(self, *args, **kwargs):
        self.state = {
            'last_command': 'echo',
            'working_dir': '/',
            'file_list': [],
            'dir_list': [],
        }


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

    def send_command(self, cmd):
        raise NotImplementedError('Do not call base class!')

    def get_response(self):
        raise NotImplementedError('Do not call base class!')
