import os
import unittest

from hpfeeds.broker.auth.env import Authenticator

from .utils import mock


class TestAuthenticator(unittest.TestCase):

    def test_1(self):
        environ = {
            'HPFEEDS_AAA_SECRET': 'bbb',
            'HPFEEDS_AAA_OWNER': 'ccc',
            'HPFEEDS_AAA_PUBCHANS': 'a,b,c',
            'HPFEEDS_AAA_SUBCHANS': 'd,e,f',
        }

        with mock.patch.dict(os.environ, environ):
            key = Authenticator().get_authkey('aaa')

        assert key['owner'] == 'ccc'
        assert key['secret'] == 'bbb'
        assert key['pubchans'] == ['a', 'b', 'c']
        assert key['subchans'] == ['d', 'e', 'f']

    def test_2(self):
        environ = {
            'HPFEEDS_AAA_SECRET': 'bbb',
            'HPFEEDS_AAA_PUBCHANS': 'a,b,c',
            'HPFEEDS_AAA_SUBCHANS': 'd,e,f',
        }

        with mock.patch.dict(os.environ, environ):
            key = Authenticator().get_authkey('aaa')

        assert key['owner'] == 'aaa'
        assert key['secret'] == 'bbb'
        assert key['pubchans'] == ['a', 'b', 'c']
        assert key['subchans'] == ['d', 'e', 'f']
