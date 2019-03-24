import unittest

from hpfeeds.twisted import BaseProtocol, ClientProtocol

from .utils import mock


class TestTwistedBaseProtocol(unittest.TestCase):

    def setUp(self):
        self.protocol = BaseProtocol()
        self.transport = self.patch_object(self.protocol, 'transport')

    def patch_object(self, *args, **kwargs):
        patcher = mock.patch.object(*args, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def test_onError(self):
        self.assertRaises(NotImplementedError, self.protocol.onError, 'error')

    def test_onInfo(self):
        self.assertRaises(NotImplementedError, self.protocol.onInfo, 'name', b'rand')

    def test_onAuth(self):
        self.assertRaises(NotImplementedError, self.protocol.onAuth, 'name', b'rand')

    def test_onPublish(self):
        self.assertRaises(NotImplementedError, self.protocol.onPublish, 'ident', 'chan', 'data')

    def test_onSubscribe(self):
        self.assertRaises(NotImplementedError, self.protocol.onSubscribe, 'ident', 'chan')

    def test_onUnsubscribe(self):
        self.assertRaises(NotImplementedError, self.protocol.onUnsubscribe, 'ident', 'chan')

    def test_error(self):
        self.protocol.error('error')
        assert self.transport.write.call_args[0][0] == b'\x00\x00\x00\n\x00error'

    def test_info(self):
        self.protocol.info('name', b'\x00' * 4)
        assert self.transport.write.call_args[0][0] == b'\x00\x00\x00\x0e\x01\x04name\x00\x00\x00\x00'

    def test_auth(self):
        self.protocol.auth(b'\x00' * 4, 'ident', 'secret')
        assert self.transport.write.call_args[0][0] == \
            b'\x00\x00\x00\x1f\x02\x05ident\x16\xa3\x11\xd5\xc2`\xcd\xc1\xee\xf3\x8b\xaf"\xdf\x97\x18\x90t&\xac'

    def test_publish(self):
        self.protocol.publish('ident', 'chan', 'payload')
        assert self.transport.write.call_args[0][0] == b'\x00\x00\x00\x17\x03\x05ident\x04chanpayload'

    def test_subscribe(self):
        self.protocol.subscribe('ident', 'chan')
        assert self.transport.write.call_args[0][0] == b'\x00\x00\x00\x0f\x04\x05identchan'

    def test_unsubscribe(self):
        self.protocol.unsubscribe('ident', 'chan')
        assert self.transport.write.call_args[0][0] == b'\x00\x00\x00\x0f\x05\x05identchan'

    def test_protocolError(self):
        self.protocol.protocolError('reason')


class TestTwistedBaseProtocolDecoding(unittest.TestCase):

    def setUp(self):
        self.protocol = BaseProtocol()
        self.onError = self.patch_object(self.protocol, 'onError')
        self.onInfo = self.patch_object(self.protocol, 'onInfo')
        self.onAuth = self.patch_object(self.protocol, 'onAuth')
        self.onPublish = self.patch_object(self.protocol, 'onPublish')
        self.onSubscribe = self.patch_object(self.protocol, 'onSubscribe')
        self.onUnsubscribe = self.patch_object(self.protocol, 'onUnsubscribe')
        self.protocolError = self.patch_object(self.protocol, 'protocolError')
        self.transport = self.patch_object(self.protocol, 'transport')

    def patch_object(self, *args, **kwargs):
        patcher = mock.patch.object(*args, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def test_onError(self):
        self.protocol.dataReceived(b'\x00\x00\x00\n\x00error')
        assert self.onError.call_args[0][0] == 'error'

    def test_onInfo(self):
        self.protocol.dataReceived(b'\x00\x00\x00\x0e\x01\x04name\x00\x00\x00\x00')
        assert self.onInfo.call_args[0][0] == 'name'
        assert self.onInfo.call_args[0][1] == b'\x00' * 4

    def test_onAuth(self):
        self.protocol.dataReceived(b'\x00\x00\x00\x1f\x02\x05ident\x16\xa3\x11\xd5\xc2`\xcd\xc1\xee\xf3\x8b\xaf"\xdf\x97\x18\x90t&\xac')
        assert self.onAuth.call_args[0][0] == 'ident'
        assert self.onAuth.call_args[0][1] == b'\x16\xa3\x11\xd5\xc2`\xcd\xc1\xee\xf3\x8b\xaf"\xdf\x97\x18\x90t&\xac'

    def test_onPublish(self):
        self.protocol.dataReceived(b'\x00\x00\x00\x17\x03\x05ident\x04chanpayload')
        assert self.onPublish.call_args[0][0] == 'ident'
        assert self.onPublish.call_args[0][1] == 'chan'
        assert self.onPublish.call_args[0][2] == b'payload'

    def test_onSubscribe(self):
        self.protocol.dataReceived(b'\x00\x00\x00\x0f\x04\x05identchan')
        assert self.onSubscribe.call_args[0][0] == 'ident'
        assert self.onSubscribe.call_args[0][1] == 'chan'

    def test_onUnsubscribe(self):
        self.protocol.dataReceived(b'\x00\x00\x00\x0f\x05\x05identchan')
        assert self.onUnsubscribe.call_args[0][0] == 'ident'
        assert self.onUnsubscribe.call_args[0][1] == 'chan'

    def test_invalid_opcode(self):
        # We test this seperately as the unpacker also enforces valid opcodes
        # So normally this won't be hit.
        self.protocol.messageReceived(77, b'\x05identchan')
        assert self.protocolError.call_args[0][0] == 'Unknown message opcode: 77'
        self.transport.loseConnection.assert_called_with()

    def test_invalid_opcode_2(self):
        self.protocol.dataReceived(b'\x00\x00\x00\x0f\x06\x05identchan')
        assert self.protocolError.call_args[0][0] == 'Unknown opcode: 6'
        self.transport.loseConnection.assert_called_with()

    def test_invalid_size(self):
        self.protocol.dataReceived(b'\x00\xff\xff\xff\x05\x05identchan')
        assert self.protocolError.call_args[0][0] == 'Message too big; op 5 ml: 16777215 max_ml: 1048576'
        self.transport.loseConnection.assert_called_with()


class TestTwistedClientProtocol(unittest.TestCase):

    def setUp(self):
        self.protocol = ClientProtocol()

        self.protocol.factory = mock.Mock()
        self.protocol.factory.ident = 'ident'
        self.protocol.factory.secret = 'secret'

        self.transport = self.patch_object(self.protocol, 'transport')
        self.connectionReady = self.patch_object(self.protocol, 'connectionReady')
        self.protocolError = self.patch_object(self.protocol, 'protocolError')

    def patch_object(self, *args, **kwargs):
        patcher = mock.patch.object(*args, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def test_connectionReady(self):
        self.protocol.connectionReady()

    def test_onInfo(self):
        # A client should auto-reply to an OP_INFO the call connectionReady
        self.protocol.onInfo('hpfeeds', b'\x00' * 4)
        assert self.transport.write.call_args[0][0] == \
            b'\x00\x00\x00\x1f\x02\x05ident\x16\xa3\x11\xd5\xc2`\xcd\xc1\xee\xf3\x8b\xaf"\xdf\x97\x18\x90t&\xac'

    def test_onAuth(self):
        ''' Client should never receive an OP_AUTH message - it is an error if it does '''
        self.protocol.dataReceived(b'\x00\x00\x00\x1f\x02\x05ident\x16\xa3\x11\xd5\xc2`\xcd\xc1\xee\xf3\x8b\xaf"\xdf\x97\x18\x90t&\xac')
        assert self.protocolError.call_args[0][0] == 'Unexpected OP_AUTH'
        self.transport.loseConnection.assert_called_with()

    def test_onSubscribe(self):
        ''' Client should never receive an OP_SUBSCRIBE message - it is an error if it does '''
        self.protocol.dataReceived(b'\x00\x00\x00\x0f\x04\x05identchan')
        assert self.protocolError.call_args[0][0] == 'Unexpected OP_SUBSCRIBE'
        self.transport.loseConnection.assert_called_with()

    def test_onUnsubscribe(self):
        ''' Client should never receive an OP_UNSUBSCRIBE message - it is an error if it does '''
        self.protocol.dataReceived(b'\x00\x00\x00\x0f\x05\x05identchan')
        assert self.protocolError.call_args[0][0] == 'Unexpected OP_UNSUBSCRIBE'
        self.transport.loseConnection.assert_called_with()

    def test_error(self):
        self.assertRaises(RuntimeError, self.protocol.error, 'error')

    def test_info(self):
        self.assertRaises(RuntimeError, self.protocol.info, 'name', b'\x00' * 4)


class TestTwistedClientProtocolConnReady(unittest.TestCase):

    def test_connectionReady(self):
        self.protocol = ClientProtocol()
        self.protocol.connectionReady()
