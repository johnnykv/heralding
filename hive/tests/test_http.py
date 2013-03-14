import gevent
import gevent.monkey
gevent.monkey.patch_all()


from gevent.server import StreamServer
from hive.helpers.common import create_socket
from hive.capabilities import http


import unittest
import httplib

class HTTP_Test(unittest.TestCase):
    def test_connection(self):
        """ Tests if the capability is up, and sending
            HTTP 401 (Unauthorized) headers.
        """
        sessions = {}
        cap = http.http(sessions, {'enabled': 'True', 'port': 8080})
        socket = create_socket(("0.0.0.0", 8080))
        srv = StreamServer(socket, cap.handle_session)
        srv.start()

        client = httplib.HTTPConnection('127.0.0.1', 8080)
        client.request("GET", "/")
        response = client.getresponse()
        self.assertEquals(response.status, 401)
        
if __name__ == '__main__':
    unittest.main()
