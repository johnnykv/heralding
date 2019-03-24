import unittest

from hpfeeds.broker.auth.sqlite import Authenticator


class TestAuthenticator(unittest.TestCase):

    def test_(self):
        a = Authenticator(':memory:')
        a.sql.execute(
            'INSERT INTO authkeys(owner, ident, secret, pubchans, subchans)'
            'VALUES ("a", "b", "c", "[]", "[]")'
        )
        key = a.get_authkey('b')
        assert key['owner'] == 'a'
        assert key['secret'] == 'c'
        assert key['pubchans'] == []
        assert key['subchans'] == []
