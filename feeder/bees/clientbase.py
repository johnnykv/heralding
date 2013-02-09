class ClientBase(object):
    def do_session(self, login, password, server_host, server_port, my_ip):
        raise Exception('Do not call base class!')