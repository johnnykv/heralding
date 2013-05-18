import json
import uuid
import unittest
from datetime import datetime

import gevent.monkey

gevent.monkey.patch_all()

#find better way to do this!
from beeswarm.beekeeper import database_config

database_config.setup_db(':memory:')

from beeswarm.beekeeper.webapp import app


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
            'source_ip': '123.123.123.123',
            'source_port': 12345,
            'timestamp': datetime.utcnow().isoformat(),
            'did_connect': True,
            'did_login': True,
            'did_complete': True,
            'protocol_data': None
        }

        self.app.post('/ws/feeder_data', data=json.dumps(data_dict), content_type='application/json')

    def test_basic_hive_post(self):
        """
        Tests if a session dict can be posted without exceptions.
        """
        data_dict = {
            'id': 'ba9fdb3d-0efb-4764-9a6b-d9b86eccda96',
            'hive_id': 'h11141df-b2f6-baf4-86c0-f4e163cf69aa',
            'honey_ip': '192.168.1.1',
            'honey_port': 8023,
            'protocol': 'telnet',
            'attacker_ip': '127.0.0.1',
            'timestamp': '2013-05-07T22:21:19.453828',
            'attacker_source_port': 61175,
            'login_attempts': [
                {'username': 'qqq', 'timestamp': '2013-05-07T22:21:20.846805', 'password': 'aa', 'type': 'plaintext',
                 'id': '027bd968-f8ea-4a69-8d4c-6cf21476ca10'},
                {'username': 'as', 'timestamp': '2013-05-07T22:21:21.150571', 'password': 'd', 'type': 'plaintext',
                 'id': '603f40a4-e7eb-442d-9fde-0cd3ba707af7'},
                {'username': 'as', 'timestamp': '2013-05-07T22:21:21.431958', 'password': 'd', 'type': 'plaintext',
                 'id': 'ba24a095-f2c5-4426-84b9-9b7bfb609045'}]
        }

        self.app.post('/ws/hive_data', data=json.dumps(data_dict), content_type='application/json')

if __name__ == '__main__':
    unittest.main()