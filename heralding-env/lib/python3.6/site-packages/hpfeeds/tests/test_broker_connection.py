import unittest
from unittest import mock

from hpfeeds.broker import prometheus
from hpfeeds.broker.auth.memory import Authenticator
from hpfeeds.broker.connection import Connection
from hpfeeds.broker.server import Server
from hpfeeds.protocol import (
    Unpacker,
    msgauth,
    msgpublish,
    msgsubscribe,
    msgunsubscribe,
    readinfo,
    readpublish,
)


def parse(mock_write):
    unpacker = Unpacker()
    for call in mock_write.call_args_list:
        unpacker.feed(call[0][0])
    results = []
    for msg in unpacker:
        results.append(msg)
    return results


class TestBrokerConnection(unittest.TestCase):

    def setUp(self):
        prometheus.reset()

        authenticator = Authenticator({
            'test': {
                'secret': 'secret',
                'subchans': ['test-chan'],
                'pubchans': ['test-chan'],
                'owner': 'some-owner',
            }
        })

        self.server = Server(authenticator, bind='127.0.0.1:20000')

    def make_connection(self):
        transport = mock.Mock()
        transport.get_extra_info.side_effect = lambda name: ('127.0.0.1', 80) if name == 'peername' else None

        connection = Connection(self.server)
        connection.connection_made(transport)

        return connection

    def test_sends_challenge(self):
        c = self.make_connection()
        assert parse(c.transport.write)[0][1][:-4] == b'\x07hpfeeds'

    def test_must_auth(self):
        c = self.make_connection()
        c.data_received(msgpublish('a', 'b', b'c'))

        assert parse(c.transport.write)[0][1][:-4] == b'\x07hpfeeds'
        assert parse(c.transport.write)[1][1] == b'First message was not AUTH'

    def test_auth_failure_wrong_secret(self):
        c = self.make_connection()
        name, rand = readinfo(parse(c.transport.write)[0][1])
        c.data_received(msgauth(rand, 'test', 'secret2'))

        assert parse(c.transport.write)[1][1] == b'Authentication failed for test'

    def test_auth_failure_no_such_ident(self):
        c = self.make_connection()
        name, rand = readinfo(parse(c.transport.write)[0][1])
        c.data_received(msgauth(rand, 'test2', 'secret'))

        assert parse(c.transport.write)[1][1] == b'Authentication failed for test2'

    def test_permission_to_sub(self):
        c = self.make_connection()
        name, rand = readinfo(parse(c.transport.write)[0][1])
        c.data_received(msgauth(rand, 'test', 'secret'))
        c.data_received(msgsubscribe('test', 'test-chan2'))

        assert parse(c.transport.write)[1][1] == b'Authkey not allowed to sub here. ident=test, chan=test-chan2'

    def test_permission_to_pub(self):
        c = self.make_connection()
        name, rand = readinfo(parse(c.transport.write)[0][1])
        c.data_received(msgauth(rand, 'test', 'secret'))
        c.data_received(msgpublish('test', 'test-chan2', b'c'))

        assert parse(c.transport.write)[1][1] == b'Authkey not allowed to pub here. ident=test, chan=test-chan2'

    def test_pub_ident_checked(self):
        c = self.make_connection()
        name, rand = readinfo(parse(c.transport.write)[0][1])
        c.data_received(msgauth(rand, 'test', 'secret'))
        c.data_received(msgpublish('wrong-ident', 'test-chan2', b'c'))

        assert parse(c.transport.write)[1][1] == b'Invalid authkey in message, ident=wrong-ident'

    def test_auth_success(self):
        c = self.make_connection()
        name, rand = readinfo(parse(c.transport.write)[0][1])
        c.data_received(msgauth(rand, 'test', 'secret'))
        c.data_received(msgsubscribe('test', 'test-chan'))
        c.data_received(msgpublish('test', 'test-chan', b'c'))

        assert readpublish(parse(c.transport.write)[1][1]) == (
            'test',
            'test-chan',
            b'c'
        )

    def test_multiple_subscribers(self):
        subscribers = []
        for i in range(5):
            c = self.make_connection()
            name, rand = readinfo(parse(c.transport.write)[0][1])
            c.data_received(msgauth(rand, 'test', 'secret'))
            c.data_received(msgsubscribe('test', 'test-chan'))
            subscribers.append(c)

        c = self.make_connection()
        name, rand = readinfo(parse(c.transport.write)[0][1])
        c.data_received(msgauth(rand, 'test', 'secret'))
        c.data_received(msgpublish('test', 'test-chan', b'c'))

        for c in subscribers:
            msgs = parse(c.transport.write)
            assert readpublish(msgs[1][1]) == (
                'test',
                'test-chan',
                b'c'
            )

    def test_auth_unsubscribe(self):
        c = self.make_connection()
        name, rand = readinfo(parse(c.transport.write)[0][1])
        c.data_received(msgauth(rand, 'test', 'secret'))

        c.data_received(msgsubscribe('test', 'test-chan'))
        c.data_received(msgpublish('test', 'test-chan', b'c'))
        c.data_received(msgunsubscribe('test', 'test-chan'))
        c.data_received(msgpublish('test', 'test-chan', b'c'))
        c.data_received(msgsubscribe('test', 'test-chan'))
        c.data_received(msgpublish('test', 'test-chan', b'c'))

        messages = parse(c.transport.write)
        for msg in messages[1:]:
            assert readpublish(msg[1]) == (
                'test',
                'test-chan',
                b'c'
            )

        # 1 auth and 2 publish
        assert len(messages) == 3
