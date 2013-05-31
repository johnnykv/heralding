import json
import uuid
import unittest
from datetime import datetime

import gevent.monkey
gevent.monkey.patch_all()

from pony.orm import commit, select
from beeswarm.beekeeper.db import database_config
database_config.setup_db(':memory:')

from beeswarm.beekeeper.db.database import Hive, Classification, Feeder
from beeswarm.beekeeper.webapp import app


class WebappTests(unittest.TestCase):
    def setUp(self):
        self.app = app.app.test_client()

        #setup dummy entities
        self.feeder_id =  str(uuid.uuid4())
        _feeder = Feeder(id=self.feeder_id)
        self.hive_id = str(uuid.uuid4())
        _hive = Hive(id=self.hive_id)
        commit()

    def tearDown(self):
        database_config.clear_db()

    def test_basic_feeder_post(self):
        """
        Tests if a honeybee dict can be posted without exceptions.
        """

        data_dict = {
            'id': str(uuid.uuid4()),
            'feeder_id': self.feeder_id,
            'hive_id': self.hive_id,
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
            'hive_id': self.hive_id,
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

    def test_new_feeder_configuration(self):
        """
        Tests if a new Feeder configuration can be posted successfully
        """

        post_data = {
            'http_enabled': True,
            'http_server': '127.0.0.1',
            'http_port': 80,
            'http_timing': 'regular',
            'http_login': 'test',
            'http_password': 'test',

            'pop3_enabled': True,
            'pop3_server': '127.0.0.1',
            'pop3_port': 110,
            'pop3_timing': 'regular',
            'pop3_login': 'test',
            'pop3_password': 'test',

            'smtp_enabled': True,
            'smtp_server': '127.0.0.1',
            'smtp_port': 25,
            'smtp_timing': 'regular',
            'smtp_login': 'test',
            'smtp_password': 'test',

            'vnc_enabled': True,
            'vnc_server': '127.0.0.1',
            'vnc_port': 5900,
            'vnc_timing': 'regular',
            'vnc_login': 'test',
            'vnc_password': 'test',

            'telnet_enabled': True,
            'telnet_server': '127.0.0.1',
            'telnet_port': 23,
            'telnet_timing': 'regular',
            'telnet_login': 'test',
            'telnet_password': 'test',
        }
        self.app.post('/ws/feeder', data=post_data)

    def test_new_hive_configuration(self):
        """
        Tests whether new Hive configuration can be posted successfully.
        """
        post_data = {
            'http_enabled': True,
            'http_port': 80,
            'http_banner': 'Microsoft-IIS/5.0',

            'https_enabled': False,
            'https_port': 443,
            'https_banner': 'Microsoft-IIS/5.0',

            'ftp_enabled': False,
            'ftp_port': 21,
            'ftp_max_attempts': 3,
            'ftp_banner': 'Microsoft FTP Server',

            'smtp_enabled': False,
            'smtp_port': 25,
            'smtp_banner': 'Microsoft ESMTP MAIL service ready',

            'vnc_enabled': False,
            'vnc_port': 5900,

            'telnet_enabled': False,
            'telnet_port': 23,
            'telnet_max_attempts': 3,

            'pop3_enabled': False,
            'pop3_port': 110,
            'pop3_max_attempts': 3,

            'pop3s_enabled': False,
            'pop3s_port': 110,
            'pop3s_max_attempts': 3,

            'ssh_enabled': False,
            'ssh_port': 22,
            'ssh_key': 'server.key'
        }
        self.app.post('/ws/hive', data=post_data)


if __name__ == '__main__':
    unittest.main()