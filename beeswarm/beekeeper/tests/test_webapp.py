import json
import uuid
import unittest
from datetime import datetime

import gevent.monkey
from beeswarm.beekeeper.webapp.auth import Authenticator
from beeswarm.shared.helpers import is_url
gevent.monkey.patch_all()


from beeswarm.beekeeper.db import database
from beeswarm.beekeeper.db.entities import Feeder, Hive, Session, Honeybee, User
from beeswarm.beekeeper.webapp import app
app.app.config['CSRF_ENABLED'] = False


class WebappTests(unittest.TestCase):
    def setUp(self):
        self.app = app.app.test_client()
        self.authenticator = Authenticator()

        database.setup_db('sqlite://')
        session = database.get_session()

        #setup dummy entities
        self.authenticator.add_user('test', 'test', 'Nick Name')
        self.feeder_id = str(uuid.uuid4())
        feeder = Feeder(id=self.feeder_id, configuration='test_feeder_config')
        self.hive_id = str(uuid.uuid4())
        hive = Hive(id=self.hive_id, configuration='test_hive_config')
        session.add_all([feeder, hive])
        session.commit()

    def tearDown(self):
        database.clear_db()

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

    def test_new_feeder(self):
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
        self.login('test', 'test')
        resp = self.app.post('/ws/feeder', data=post_data)
        self.assertTrue(is_url(resp.data))
        self.assertTrue('/ws/feeder/config/' in resp.data)
        self.logout()

    def test_new_hive(self):
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
        self.login('test', 'test')
        resp = self.app.post('/ws/hive', data=post_data)
        self.assertTrue(is_url(resp.data))
        self.assertTrue('/ws/hive/config/' in resp.data)
        self.logout()

    def test_new_hive_config(self):
        """ Tests if a Hive config is being returned correctly """

        resp = self.app.get('/ws/hive/config/' + self.hive_id)
        self.assertEquals(resp.data, 'test_hive_config')

    def test_new_feeder_config(self):
        """ Tests if a Feeder config is being returned correctly """

        resp = self.app.get('/ws/feeder/config/' + self.feeder_id)
        self.assertEquals(resp.data, 'test_feeder_config')

    def test_data_sessions_all(self):
        """ Tests if all sessions are returned properly"""

        self.login('test', 'test')
        self.populate_sessions()
        resp = self.app.get('/data/sessions/all')
        table_data = json.loads(resp.data)
        self.assertEquals(len(table_data), 4)
        self.logout()

    def test_data_sessions_honeybees(self):
        """ Tests if honeybees are returned properly """

        self.login('test', 'test')
        self.populate_honeybees()
        resp = self.app.get('/data/sessions/honeybees')
        table_data = json.loads(resp.data)
        self.assertEquals(len(table_data), 3)
        self.logout()

    def test_data_sessions_attacks(self):
        """ Tests if attacks are returned properly """

        self.login('test', 'test')
        self.populate_sessions()
        resp = self.app.get('/data/sessions/attacks')
        table_data = json.loads(resp.data)
        self.assertEquals(len(table_data), 4)
        self.logout()

    def test_login_logout(self):
        """ Tests basic login/logout """

        self.login('test', 'test')
        self.logout()

    def test_hive_delete(self):
        """ Tests the '/ws/hive/delete' route."""

        self.login('test', 'test')
        self.populate_hives()
        data = [
            {'attacks': 0, 'checked': False, 'hive_id': self.hives[0]},
            {'attacks': 0, 'checked': False, 'hive_id': self.hives[1]}
        ]
        self.app.post('/ws/hive/delete', data=json.dumps(data))
        db_session = database.get_session()
        nhives = db_session.query(Hive).count()
        self.assertEquals(3, nhives)

    def test_feeder_delete(self):
        """ Tests the '/ws/feeder/delete' route."""

        self.login('test', 'test')
        self.populate_feeders()
        data = [
            {'feeder_id': self.feeders[0], 'bees': 0, 'checked': False},
            {'feeder_id': self.feeders[1], 'bees': 0, 'checked': False}
        ]
        self.app.post('/ws/feeder/delete', data=json.dumps(data))
        db_session = database.get_session()
        nfeeders = db_session.query(Feeder).count()
        self.assertEquals(3, nfeeders)

    def populate_feeders(self):
        """ Populates the database with 4 Feeders """

        db_session = database.get_session()
        self.feeders = []
        for i in xrange(4):
            curr_id = str(uuid.uuid4())
            curr_id = curr_id.encode('utf-8')
            self.feeders.append(curr_id)
            u = User(id=curr_id, password=str(uuid.uuid4()), utype=1)
            f = Feeder(id=curr_id)
            db_session.add(f)
            db_session.add(u)
        db_session.commit()

    def populate_hives(self):
        """ Populates the database with 4 Hives """

        db_session = database.get_session()
        self.hives = []
        for i in xrange(4):
            curr_id = str(uuid.uuid4())
            curr_id = curr_id.encode('utf-8')
            self.hives.append(curr_id)
            h = Hive(id=curr_id)
            u = User(id=curr_id, password=str(uuid.uuid4()), utype=1)
            db_session.add(h)
            db_session.add(u)
        db_session.commit()

    def login(self, username, password):
        """ Logs into the web-app """

        data = {
            'username': username,
            'password': password
        }
        return self.app.post('/login', data=data, follow_redirects=True)

    def populate_honeybees(self):
        """ Populates the database with 3 Honeybees """

        db_session = database.get_session()
        for i in xrange(3):
            h = Honeybee(
                id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                received=datetime.utcnow(),
                protocol='ssh',
                username='uuu',
                password='vvvv',
                destination_ip='1.2.3.4',
                destination_port=1234,
                source_ip='4.3.2.1',
                source_port=4321,
                did_connect=True,
                did_login=False,
                did_complete=True
            )
            db_session.add(h)
        db_session.commit()

    def populate_sessions(self):
        """ Populates the database with 3 Sessions """

        db_session = database.get_session()
        for i in xrange(4):
            s = Session(
                id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                received=datetime.utcnow(),
                protocol='telnet',
                username='aaa',
                password='bbb',
                destination_ip='123.123.123.123',
                destination_port=1234,
                source_ip='12.12.12.12',
                source_port=12345,
                classification_id='asd'
            )
            db_session.add(s)
        db_session.commit()

    def logout(self):
        return self.app.get('/logout', follow_redirects=True)

if __name__ == '__main__':
    unittest.main()