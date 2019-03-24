import os


def get_key(ident, value, default=None):
    ident = ident.upper()
    value = value.upper()
    key = '_'.join(('HPFEEDS', ident, value))
    return os.environ.get(key, default)


class Authenticator(object):

    '''
    Authentication class that takes a mapping of user identities and
    their permissions.

    Given environment variables:

        HPFEEDS_IDENT1_SECRET=secret1
        HPFEEDS_IDENT1_SUBCHANS=test
        HPFEEDS_IDENT1_PUBCHANS=test

    A user called `ident1` will be able to authenticate with the broker.

    authenticator = Authenticator()
    '''

    def close(self):
        pass

    def get_authkey(self, ident):
        secret = get_key(ident, 'secret')
        if not secret:
            return None

        return {
            'ident': ident,
            'owner': get_key(ident, 'owner', ident),
            'secret': secret,
            'subchans': get_key(ident, 'subchans', '').split(','),
            'pubchans': get_key(ident, 'pubchans', '').split(','),
        }
