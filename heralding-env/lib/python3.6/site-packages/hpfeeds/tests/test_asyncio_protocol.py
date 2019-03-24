import unittest
from unittest import mock

from hpfeeds.asyncio import BaseProtocol, ClientProtocol


class TestAioBaseProtocol(unittest.TestCase):

    def setUp(self):
        self.protocol = BaseProtocol()
        self.protocol.transport = mock.Mock()

    def patch_object(self, *args, **kwargs):
        patcher = mock.patch.object(*args, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def test_on_error(self):
        self.assertRaises(NotImplementedError, self.protocol.on_error, 'error')

    def test_on_info(self):
        self.assertRaises(NotImplementedError, self.protocol.on_info, 'name', b'rand')

    def test_on_auth(self):
        self.assertRaises(NotImplementedError, self.protocol.on_auth, 'name', b'rand')

    def test_on_publish(self):
        self.assertRaises(NotImplementedError, self.protocol.on_publish, 'ident', 'chan', 'data')

    def test_on_subscribe(self):
        self.assertRaises(NotImplementedError, self.protocol.on_subscribe, 'ident', 'chan')

    def test_on_unsubscribe(self):
        self.assertRaises(NotImplementedError, self.protocol.on_unsubscribe, 'ident', 'chan')

    def test_error(self):
        self.protocol.error('error')
        assert self.protocol.transport.write.call_args[0][0] == b'\x00\x00\x00\n\x00error'

    def test_info(self):
        self.protocol.info('name', b'\x00' * 4)
        assert self.protocol.transport.write.call_args[0][0] == b'\x00\x00\x00\x0e\x01\x04name\x00\x00\x00\x00'

    def test_auth(self):
        self.protocol.auth(b'\x00' * 4, 'ident', 'secret')
        assert self.protocol.transport.write.call_args[0][0] == \
            b'\x00\x00\x00\x1f\x02\x05ident\x16\xa3\x11\xd5\xc2`\xcd\xc1\xee\xf3\x8b\xaf"\xdf\x97\x18\x90t&\xac'

    def test_publish(self):
        self.protocol.publish('ident', 'chan', 'payload')
        assert self.protocol.transport.write.call_args[0][0] == b'\x00\x00\x00\x17\x03\x05ident\x04chanpayload'

    def test_subscribe(self):
        self.protocol.subscribe('ident', 'chan')
        assert self.protocol.transport.write.call_args[0][0] == b'\x00\x00\x00\x0f\x04\x05identchan'

    def test_unsubscribe(self):
        self.protocol.unsubscribe('ident', 'chan')
        assert self.protocol.transport.write.call_args[0][0] == b'\x00\x00\x00\x0f\x05\x05identchan'

    def test_protocol_error(self):
        self.protocol.protocol_error('reason')


class TestAioBaseProtocolDecoding(unittest.TestCase):

    def setUp(self):
        self.protocol = BaseProtocol()
        self.on_error = self.patch_object(self.protocol, 'on_error')
        self.on_info = self.patch_object(self.protocol, 'on_info')
        self.on_auth = self.patch_object(self.protocol, 'on_auth')
        self.on_publish = self.patch_object(self.protocol, 'on_publish')
        self.on_subscribe = self.patch_object(self.protocol, 'on_subscribe')
        self.on_unsubscribe = self.patch_object(self.protocol, 'on_unsubscribe')
        self.protocol_error = self.patch_object(self.protocol, 'protocol_error')
        self.protocol.transport = mock.Mock()

    def patch_object(self, *args, **kwargs):
        patcher = mock.patch.object(*args, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def test_on_error(self):
        self.protocol.data_received(b'\x00\x00\x00\n\x00error')
        assert self.on_error.call_args[0][0] == 'error'

    def test_on_info(self):
        self.protocol.data_received(b'\x00\x00\x00\x0e\x01\x04name\x00\x00\x00\x00')
        assert self.on_info.call_args[0][0] == 'name'
        assert self.on_info.call_args[0][1] == b'\x00' * 4

    def test_on_auth(self):
        self.protocol.data_received(b'\x00\x00\x00\x1f\x02\x05ident\x16\xa3\x11\xd5\xc2`\xcd\xc1\xee\xf3\x8b\xaf"\xdf\x97\x18\x90t&\xac')
        assert self.on_auth.call_args[0][0] == 'ident'
        assert self.on_auth.call_args[0][1] == b'\x16\xa3\x11\xd5\xc2`\xcd\xc1\xee\xf3\x8b\xaf"\xdf\x97\x18\x90t&\xac'

    def test_on_publish(self):
        self.protocol.data_received(b'\x00\x00\x00\x17\x03\x05ident\x04chanpayload')
        assert self.on_publish.call_args[0][0] == 'ident'
        assert self.on_publish.call_args[0][1] == 'chan'
        assert self.on_publish.call_args[0][2] == b'payload'

    def test_on_subscribe(self):
        self.protocol.data_received(b'\x00\x00\x00\x0f\x04\x05identchan')
        assert self.on_subscribe.call_args[0][0] == 'ident'
        assert self.on_subscribe.call_args[0][1] == 'chan'

    def test_on_unsubscribe(self):
        self.protocol.data_received(b'\x00\x00\x00\x0f\x05\x05identchan')
        assert self.on_unsubscribe.call_args[0][0] == 'ident'
        assert self.on_unsubscribe.call_args[0][1] == 'chan'

    def test_invalid_opcode(self):
        # We test this seperately as the unpacker also enforces valid opcodes
        # So normally this won't be hit.
        self.protocol.message_received(77, b'\x05identchan')
        assert self.protocol_error.call_args[0][0] == 'Unknown message opcode: 77'
        self.protocol.transport.close.assert_called_with()

    def test_invalid_opcode_2(self):
        self.protocol.data_received(b'\x00\x00\x00\x0f\x06\x05identchan')
        assert self.protocol_error.call_args[0][0] == 'Unknown opcode: 6'
        self.protocol.transport.close.assert_called_with()

    def test_invalid_size(self):
        self.protocol.data_received(b'\x00\xff\xff\xff\x05\x05identchan')
        assert self.protocol_error.call_args[0][0] == 'Message too big; op 5 ml: 16777215 max_ml: 1048576'
        self.protocol.transport.close.assert_called_with()


class TestAioClientProtocol(unittest.TestCase):

    def setUp(self):
        self.protocol = ClientProtocol('ident', 'secret')
        self.protocol.transport = mock.Mock()

        self.connection_ready = self.patch_object(self.protocol, 'connection_ready')
        self.protocol_error = self.patch_object(self.protocol, 'protocol_error')

    def patch_object(self, *args, **kwargs):
        patcher = mock.patch.object(*args, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def test_connection_ready(self):
        self.protocol.connection_ready()

    def test_on_info(self):
        # A client should auto-reply to an OP_INFO the call connection_ready
        self.protocol.on_info('hpfeeds', b'\x00' * 4)
        assert self.protocol.transport.write.call_args[0][0] == \
            b'\x00\x00\x00\x1f\x02\x05ident\x16\xa3\x11\xd5\xc2`\xcd\xc1\xee\xf3\x8b\xaf"\xdf\x97\x18\x90t&\xac'

    def test_on_auth(self):
        ''' Client should never receive an OP_AUTH message - it is an error if it does '''
        self.protocol.data_received(b'\x00\x00\x00\x1f\x02\x05ident\x16\xa3\x11\xd5\xc2`\xcd\xc1\xee\xf3\x8b\xaf"\xdf\x97\x18\x90t&\xac')
        assert self.protocol_error.call_args[0][0] == 'Unexpected OP_AUTH'
        self.protocol.transport.close.assert_called_with()

    def test_on_subscribe(self):
        ''' Client should never receive an OP_SUBSCRIBE message - it is an error if it does '''
        self.protocol.data_received(b'\x00\x00\x00\x0f\x04\x05identchan')
        assert self.protocol_error.call_args[0][0] == 'Unexpected OP_SUBSCRIBE'
        self.protocol.transport.close.assert_called_with()

    def test_on_unsubscribe(self):
        ''' Client should never receive an OP_UNSUBSCRIBE message - it is an error if it does '''
        self.protocol.data_received(b'\x00\x00\x00\x0f\x05\x05identchan')
        assert self.protocol_error.call_args[0][0] == 'Unexpected OP_UNSUBSCRIBE'
        self.protocol.transport.close.assert_called_with()

    def test_error(self):
        self.assertRaises(RuntimeError, self.protocol.error, 'error')

    def test_info(self):
        self.assertRaises(RuntimeError, self.protocol.info, 'name', b'\x00' * 4)


class TestAioClientProtocolConnReady(unittest.TestCase):

    def test_connection_ready(self):
        self.protocol = ClientProtocol('ident', 'secret')
        self.protocol.connection_ready()
