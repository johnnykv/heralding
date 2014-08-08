import json
import os
import uuid
import unittest
import tempfile
import shutil
from datetime import datetime

from beeswarm.server.webapp.auth import Authenticator
from beeswarm.server.misc.config_actor import ConfigActor
import beeswarm.server.db.database_setup as database
from beeswarm.server.db.entities import Client, Honeypot, Session, BaitSession, User, \
    Authentication, Transcript, BaitUser
from beeswarm.server.webapp import app


class WebappTests(unittest.TestCase):
    def setUp(self):
        app.app.config['WTF_CSRF_ENABLED'] = False
        app.app.config['CERT_PATH'] = os.path.join(os.path.dirname(__file__), 'beeswarmcfg.json.test')
        app.app.config['SERVER_CONFIG'] = os.path.join(os.path.dirname(__file__), 'beeswarmcfg.json.test')
        self.work_dir = tempfile.mkdtemp()
        self.config_actor = ConfigActor(os.path.join(os.path.dirname(__file__), 'beeswarmcfg.json.test'), self.work_dir)
        self.config_actor.start()
        self.app = app.app.test_client()
        self.authenticator = Authenticator()

        database.setup_db('sqlite://')
        session = database.get_session()

        # dummy entities
        self.authenticator.add_user('test', 'test', 0)

        self.client_id = str(uuid.uuid4())
        self.client_password = str(uuid.uuid4())
        self.authenticator.add_user(self.client_id, self.client_password, 2)

        self.honeypot_id = str(uuid.uuid4())
        self.honeypot_password = str(uuid.uuid4())
        self.authenticator.add_user(self.honeypot_id, self.honeypot_password, 1)

        session.add_all([Client(id=self.client_id, configuration='test_client_config'),
                         Honeypot(id=self.honeypot_id, configuration='test_honeypot_config')])

        session.commit()

    def tearDown(self):
        database.clear_db()
        self.config_actor.close()
        shutil.rmtree(self.work_dir)

    # TODO: All these posts should be moved to ZMQ tests
    # def test_basic_client_post(self):
    # """
    # Tests if a bait_session dict can be posted without exceptions.
    # """
    #     self.login(self.client_id, self.client_password)
    #     data_dict = {
    #         'id': str(uuid.uuid4()),
    #         'client_id': self.client_id,
    #         'honeypot_id': self.honeypot_id,
    #         'protocol': 'pop3',
    #         'destination_ip': '127.0.0.1',
    #         'destination_port': '110',
    #         'source_ip': '123.123.123.123',
    #         'source_port': 12345,
    #         'timestamp': datetime.utcnow().isoformat(),
    #         'did_connect': True,
    #         'did_login': True,
    #         'did_complete': True,
    #         'protocol_data': None,
    #         'login_attempts': [{'id': str(uuid.uuid4()), 'username': 'james', 'password': 'bond', 'successful': True,
    #                             'timestamp': datetime.utcnow().isoformat()}]
    #     }
    #     r = self.app.post('/ws/client_data', data=json.dumps(data_dict), content_type='application/json')
    #     self.assertEquals(r.status, '200 OK')
    #
    # def test_basic_unsuccessful_client_post(self):
    #     """
    #     Tests if an error is returned when data is posted without ID values.
    #     """
    #
    #     self.login(self.client_id, self.client_password)
    #
    #     #missing id's
    #     data_dict = {
    #         'protocol': 'pop3',
    #         'username': 'james',
    #         'password': 'bond',
    #         'server_host': '127.0.0.1',
    #         'server_port': '110',
    #         'source_ip': '123.123.123.123',
    #         'source_port': 12345,
    #         'timestamp': datetime.utcnow().isoformat(),
    #         'did_connect': True,
    #         'did_login': True,
    #         'did_complete': True,
    #         'protocol_data': None
    #     }
    #
    #     r = self.app.post('/ws/client_data', data=json.dumps(data_dict), content_type='application/json')
    #     self.assertEquals(r.status, '500 INTERNAL SERVER ERROR')
    #
    # def test_basic_honeypot_post(self):
    #     """
    #     Tests if a session dict can be posted without exceptions.
    #     """
    #
    #     self.login(self.honeypot_id, self.honeypot_password)
    #
    #     data_dict = {
    #         'id': 'ba9fdb3d-0efb-4764-9a6b-d9b86eccda96',
    #         'honeypot_id': self.honeypot_id,
    #         'destination_ip': '192.168.1.1',
    #         'destination_port': 8023,
    #         'protocol': 'telnet',
    #         'source_ip': '127.0.0.1',
    #         'timestamp': '2013-05-07T22:21:19.453828',
    #         'source_port': 61175,
    #         'login_attempts': [
    #             {'username': 'qqq', 'timestamp': '2013-05-07T22:21:20.846805', 'password': 'aa',
    #              'id': '027bd968-f8ea-4a69-8d4c-6cf21476ca10', 'successful': False},
    #             {'username': 'as', 'timestamp': '2013-05-07T22:21:21.150571', 'password': 'd',
    #              'id': '603f40a4-e7eb-442d-9fde-0cd3ba707af7', 'successful': False}, ],
    #         'transcript': [
    #             {'timestamp': '2013-05-07T22:21:20.846805', 'direction': 'in', 'data': 'whoami\r\n'},
    #             {'timestamp': '2013-05-07T22:21:21.136800', 'direction': 'out', 'data': 'james_brown\r\n$:~'}]
    #     }
    #
    #     r = self.app.post('/ws/honeypot_data', data=json.dumps(data_dict), content_type='application/json')
    #     self.assertEquals(r.status, '200 OK')
    #
    # def test_basic_unsuccessful_honeypot_post(self):
    #     """
    #     Tests if an error is returned when data is posted without ID values.
    #     """
    #
    #     self.login(self.honeypot_id, self.honeypot_password)
    #
    #     #missing id
    #     data_dict = {
    #         'honeypot_id': self.honeypot_id,
    #         'destination_ip': '192.168.1.1',
    #         'destination_port': 8023,
    #         'protocol': 'telnet',
    #         'source_ip': '127.0.0.1',
    #         'timestamp': '2013-05-07T22:21:19.453828',
    #         'source_port': 61175,
    #         'login_attempts': [
    #             {'username': 'qqq', 'timestamp': '2013-05-07T22:21:20.846805', 'password': 'aa',
    #              'id': '027bd968-f8ea-4a69-8d4c-6cf21476ca10', 'successful': False},
    #             {'username': 'as', 'timestamp': '2013-05-07T22:21:21.150571', 'password': 'd',
    #              'id': '603f40a4-e7eb-442d-9fde-0cd3ba707af7', 'successful': False}, ],
    #         'transcript': [
    #             {'timestamp': '2013-05-07T22:21:20.846805', 'direction': 'in', 'data': 'whoami\r\n'},
    #             {'timestamp': '2013-05-07T22:21:21.136800', 'direction': 'out', 'data': 'james_brown\r\n$:~'}
    #         ]
    #     }
    #     r = self.app.post('/ws/honeypot_data', data=json.dumps(data_dict), content_type='application/json')
    #     self.assertEquals(r.status, '500 INTERNAL SERVER ERROR')
    #
    # def test_new_client(self):
    #     """
    #     Tests if a new Client configuration can be posted successfully
    #     """
    #
    #     post_data = {
    #         'http_enabled': True,
    #         'http_server': '127.0.0.1',
    #         'http_port': 80,
    #         'http_active_range': '13:40 - 16:30',
    #         'http_sleep_interval': 0,
    #         'http_activation_probability': 1,
    #         'http_login': 'test',
    #         'http_password': 'test',
    #
    #         'https_enabled': True,
    #         'https_server': '127.0.0.1',
    #         'https_port': 80,
    #         'https_active_range': '13:40 - 16:30',
    #         'https_sleep_interval': 0,
    #         'https_activation_probability': 1,
    #         'https_login': 'test',
    #         'https_password': 'test',
    #
    #         'pop3s_enabled': True,
    #         'pop3s_server': '127.0.0.1',
    #         'pop3s_port': 80,
    #         'pop3s_active_range': '13:40 - 16:30',
    #         'pop3s_sleep_interval': 0,
    #         'pop3s_activation_probability': 1,
    #         'pop3s_login': 'test',
    #         'pop3s_password': 'test',
    #
    #         'ssh_enabled': True,
    #         'ssh_server': '127.0.0.1',
    #         'ssh_port': 80,
    #         'ssh_active_range': '13:40 - 16:30',
    #         'ssh_sleep_interval': 0,
    #         'ssh_activation_probability': 1,
    #         'ssh_login': 'test',
    #         'ssh_password': 'test',
    #
    #         'ftp_enabled': True,
    #         'ftp_server': '127.0.0.1',
    #         'ftp_port': 80,
    #         'ftp_active_range': '13:40 - 16:30',
    #         'ftp_sleep_interval': 0,
    #         'ftp_activation_probability': 1,
    #         'ftp_login': 'test',
    #         'ftp_password': 'test',
    #
    #         'pop3_enabled': True,
    #         'pop3_server': '127.0.0.1',
    #         'pop3_port': 110,
    #         'pop3_active_range': '13:40 - 16:30',
    #         'pop3_sleep_interval': 0,
    #         'pop3_activation_probability': 1,
    #         'pop3_login': 'test',
    #         'pop3_password': 'test',
    #
    #         'smtp_enabled': True,
    #         'smtp_server': '127.0.0.1',
    #         'smtp_port': 25,
    #         'smtp_active_range': '13:40 - 16:30',
    #         'smtp_sleep_interval': 0,
    #         'smtp_activation_probability': 1,
    #         'smtp_login': 'test',
    #         'smtp_password': 'test',
    #
    #         'vnc_enabled': True,
    #         'vnc_server': '127.0.0.1',
    #         'vnc_port': 5900,
    #         'vnc_active_range': '13:40 - 16:30',
    #         'vnc_sleep_interval': 0,
    #         'vnc_activation_probability': 1,
    #         'vnc_login': 'test',
    #         'vnc_password': 'test',
    #
    #         'telnet_enabled': True,
    #         'telnet_server': '127.0.0.1',
    #         'telnet_port': 23,
    #         'telnet_active_range': '13:40 - 16:30',
    #         'telnet_sleep_interval': 0,
    #         'telnet_activation_probability': 1,
    #         'telnet_login': 'test',
    #         'telnet_password': 'test',
    #     }
    #     self.login('test', 'test')
    #     resp = self.app.post('/ws/client', data=post_data)
    #     self.assertTrue(200, resp.status_code)
    #     self.logout()
    #
    # def test_new_honeypot(self):
    #     """
    #     Tests whether new Honeypot configuration can be posted successfully.
    #     """
    #     post_data = {
    #         'http_enabled': True,
    #         'http_port': 80,
    #         'http_banner': 'Microsoft-IIS/5.0',
    #
    #         'https_enabled': False,
    #         'https_port': 443,
    #         'https_banner': 'Microsoft-IIS/5.0',
    #
    #         'ftp_enabled': False,
    #         'ftp_port': 21,
    #         'ftp_max_attempts': 3,
    #         'ftp_banner': 'Microsoft FTP Server',
    #
    #         'smtp_enabled': False,
    #         'smtp_port': 25,
    #         'smtp_banner': 'Microsoft ESMTP MAIL service ready',
    #
    #         'vnc_enabled': False,
    #         'vnc_port': 5900,
    #
    #         'telnet_enabled': False,
    #         'telnet_port': 23,
    #         'telnet_max_attempts': 3,
    #
    #         'pop3_enabled': False,
    #         'pop3_port': 110,
    #         'pop3_max_attempts': 3,
    #
    #         'pop3s_enabled': False,
    #         'pop3s_port': 110,
    #         'pop3s_max_attempts': 3,
    #
    #         'ssh_enabled': False,
    #         'ssh_port': 22,
    #         'ssh_key': 'server.key'
    #     }
    #     self.login('test', 'test')
    #     resp = self.app.post('/ws/honeypot', data=post_data)
    #     self.assertTrue(200, resp.status_code)
    #     self.logout()
    #
    # def test_new_honeypot_config(self):
    #     """ Tests if a Honeypot config is being returned correctly """
    #
    #     resp = self.app.get('/ws/honeypot/config/' + self.honeypot_id)
    #     self.assertEquals(resp.data, 'test_honeypot_config')
    #
    # def test_new_client_config(self):
    #     """ Tests if a Client config is being returned correctly """
    #
    #     resp = self.app.get('/ws/client/config/' + self.client_id)
    #     self.assertEquals(resp.data, 'test_client_config')

    def test_data_sessions_all(self):
        """ Tests if all sessions are returned properly"""

        self.login('test', 'test')
        self.populate_sessions()
        resp = self.app.get('/data/sessions/all')
        table_data = json.loads(resp.data)
        self.assertEquals(len(table_data), 4)
        self.logout()

    def test_data_sessions_honeybees(self):
        """ Tests if bait_sessions are returned properly """

        self.login('test', 'test')
        self.populate_honeybees()
        resp = self.app.get('/data/sessions/bait_sessions')
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

    def test_data_honeypot(self):
        """ Tests if Honeypot information is returned properly """

        self.login('test', 'test')
        self.populate_honeypots()
        resp = self.app.get('/data/honeypots')
        table_data = json.loads(resp.data)
        self.assertEquals(len(table_data), 5)  # One is added in the setup method, and 4 in populate

    def test_data_client(self):
        """ Tests if Client information is returned properly """

        self.login('test', 'test')
        self.populate_clients()
        resp = self.app.get('/data/clients')
        table_data = json.loads(resp.data)
        self.assertEquals(len(table_data), 5)  # One is added in the setup method, and 4 in populate

    def test_data_transcripts(self):
        """ Tests that if given a session ID we can extract the relevant transcripts"""
        db_session = database.get_session()
        self.login('test', 'test')
        session_id = str(uuid.uuid4())

        timestamp = datetime.utcnow()

        db_session.add(Transcript(timestamp=timestamp, direction='outgoing', data='whoami', session_id=session_id))
        db_session.add(Transcript(timestamp=timestamp, direction='outgoing', data='root\r\n', session_id=session_id))
        db_session.commit()
        resp = self.app.get('/data/session/{0}/transcript'.format(session_id))
        data = json.loads(resp.data)
        string_timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        expected_result = [{u'direction': u'outgoing', u'data': u'whoami', u'time': u'{0}'.format(string_timestamp)},
                           {u'direction': u'outgoing', u'data': u'root\r\n', u'time': u'{0}'.format(string_timestamp)}]
        self.assertDictEqual(sorted(data)[0], sorted(expected_result)[0])


    def test_settings(self):
        """ Tests if new settings are successfully written to the config file """

        self.login('test', 'test')
        with open(app.app.config['SERVER_CONFIG'], 'r') as conf:
            original_config = conf.read()
        config_modified = os.stat(app.app.config['SERVER_CONFIG']).st_mtime
        data = {
            'bait_session_retain': 3,
            'malicious_session_retain': 50,
            'ignore_failed_bait_session': False
        }
        self.app.post('/settings', data=data, follow_redirects=True)
        config_next_modified = os.stat(app.app.config['SERVER_CONFIG']).st_mtime
        self.assertTrue(config_next_modified > config_modified)

        # Restore original configuration
        with open(app.app.config['SERVER_CONFIG'], 'w') as conf:
            conf.write(original_config)

    def test_login_logout(self):
        """ Tests basic login/logout """

        self.login('test', 'test')
        self.logout()

    # def test_honeypot_delete(self):
    #     """ Tests the '/ws/honeypot/delete' route."""
    #
    #     self.login('test', 'test')
    #     self.populate_honeypots()
    #     data = [self.honeypots[0], self.honeypots[1]]
    #     self.app.post('/ws/drone/delete', data=json.dumps(data))
    #     db_session = database.get_session()
    #     honeypot_count = db_session.query(Honeypot).count()
    #     self.assertEquals(3, honeypot_count)
    #     gevent.sleep()
    #
    # def test_client_delete(self):
    #     """ Tests the '/ws/client/delete' route."""
    #
    #     self.login('test', 'test')
    #     self.populate_clients()
    #     data = [self.clients[0], self.clients[1]]
    #     print data
    #     self.app.post('/ws/drone/delete', data=json.dumps(data))
    #     gevent.sleep(1)
    #     db_session = database.get_session()
    #     nclients = db_session.query(Client).count()
    #     self.assertEquals(3, nclients)

    def test_get_baitusers(self):
        """ Tests GET on the '/ws/bait_users' route."""
        self.login('test', 'test')
        self.populate_bait_users()
        resp = self.app.get('/ws/bait_users')
        table_data = json.loads(resp.data)
        self.assertEquals(len(table_data), 2)
        self.logout()

    def test_post_baitusers(self):
        """ Tests POST on the '/ws/bait_users' route."""
        self.login('test', 'test')

        data = [
            {'username': 'userA', 'password': 'passA'},
            {'username': 'userB', 'password': 'passB'},
            {'username': 'userC', 'password': 'passC'}
        ]

        self.app.post('/ws/bait_users', data=json.dumps(data), follow_redirects=True)
        db_session = database.get_session()
        bait_user_count = db_session.query(BaitUser).count()
        self.assertEquals(bait_user_count, 3)
        self.logout()

    def populate_clients(self):
        """ Populates the database with 4 clients """

        db_session = database.get_session()
        self.clients = []
        for i in xrange(4):  # We add 4 here, but one is added in the setup method
            curr_id = str(uuid.uuid4())
            curr_id = curr_id.encode('utf-8')
            self.clients.append(curr_id)
            f = Client(id=curr_id)
            db_session.add(f)
        db_session.commit()

    def populate_honeypots(self):
        """ Populates the database with 4 honeypots """

        db_session = database.get_session()
        self.honeypots = []
        for i in xrange(4):  # We add 4 here, but one is added in the setup method
            curr_id = str(uuid.uuid4())
            curr_id = curr_id.encode('utf-8')
            self.honeypots.append(curr_id)
            h = Honeypot(id=curr_id)
            db_session.add(h)
        db_session.commit()

    def populate_bait_users(self):
        """ Populates the database with 2 bait users """
        db_session = database.get_session()
        db_session.query(BaitUser).delete()
        self.clients = []
        for c in [('userA', 'passA'), ('userB', 'passB')]:  # We add 4 here, but one is added in the setup method
            bait_user = BaitUser(username=c[0], password=c[1])
            db_session.add(bait_user)
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
            h = BaitSession(
                id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                received=datetime.utcnow(),
                protocol='ssh',
                destination_ip='1.2.3.4',
                destination_port=1234,
                source_ip='4.3.2.1',
                source_port=4321,
                did_connect=True,
                did_login=False,
                did_complete=True
            )
            a = Authentication(id=str(uuid.uuid4()), username='uuu', password='vvvv',
                               successful=False,
                               timestamp=datetime.utcnow())
            h.authentication.append(a)
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
                destination_ip='123.123.123.123',
                destination_port=1234,
                source_ip='12.12.12.12',
                source_port=12345,
                classification_id='asd'
            )
            a = Authentication(id=str(uuid.uuid4()), username='aaa', password='bbb',
                               successful=False,
                               timestamp=datetime.utcnow())
            s.authentication.append(a)
            db_session.add(s)

        db_session.commit()

    def logout(self):
        return self.app.get('/logout', follow_redirects=True)


if __name__ == '__main__':
    unittest.main()
