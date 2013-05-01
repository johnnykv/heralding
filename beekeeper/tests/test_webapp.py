import json
import uuid
import unittest
from datetime import datetime

#find better way to do this!
from beekeeper import db
db.setup_db(':memory:')

from beekeeper.webapp import app


class WebappTests(unittest.TestCase):
    def setUp(self):
        self.app = app.app.test_client()

    def tearDown(self):
        pass

    def test_basic_feeder_post(self):
        """
        Tests if a honeybee dict can be posted without exceptions.
        """
        data_dict = {
            'id': str(uuid.uuid4()),
            'feeder_id': str(uuid.uuid4()),
            'protocol': 'pop3',
            'login': 'james',
            'password': 'bond',
            'server_host': '127.0.0.1',
            'server_port': '110',
            'timestamp': datetime.utcnow().isoformat(),
            'did_connect': True,
            'did_login': True,
            'did_complete': True,
            'protocol_data': None
        }

        self.app.post('/ws/feeder_data', data=json.dumps(data_dict), content_type='application/json')


if __name__ == '__main__':
    unittest.main()