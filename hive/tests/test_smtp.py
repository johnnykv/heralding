import gevent
import gevent.monkey
import smtplib
from hive.helpers.common import create_socket
from gevent.server import StreamServer
from hive.capabilities import smtp
gevent.monkey.patch_all()



import unittest
import httplib

class SMTP_Test(unittest.TestCase):
    
    def test_connection(self):
        sessions = {}
        cap = smtp.smtp(sessions, {'enabled': 'True', 'port': 8080, 'banner': 'Test'})
        socket = create_socket(("0.0.0.0", 2525))
        srv = StreamServer(socket, cap.handle_session)
        srv.start()

        smtp_ = smtplib.SMTP('127.0.0.1', 2525, local_hostname='localhost', timeout=15)
        smtp_.ehlo()
        smtp_.quit()
if __name__ == '__main__':
    unittest.main()
