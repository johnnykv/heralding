class Authenticator(object):

    '''
    Authentication class that takes a mapping of user identities and
    their permissions.

    authenticator = Authenticator({
        'ident1': {
            'secret': 'somesecret',
            'pubchans': ['channel1'],
            'subchans': ['channel2'],
            'owner': 'youruser',
        }
    })
    '''

    def __init__(self, creds):
        self.creds = creds

    def close(self):
        pass

    def get_authkey(self, ident):
        authkey = self.creds.get(ident, None)
        if not authkey:
            return

        authkey = dict(authkey)
        authkey['ident'] = ident
        return authkey
