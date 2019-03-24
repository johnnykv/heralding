import unittest

from hpfeeds.protocol import (
    Unpacker,
    msgauth,
    msghdr,
    msgpublish,
    msgsubscribe,
    readauth,
    readinfo,
    readpublish,
    readsubscribe,
)


class TestMessageBuilder(unittest.TestCase):

    def test_msghdr(self):
        assert msghdr(1, b'abcdefg') == b'\x00\x00\x00\x0c\x01abcdefg'

    def test_msgpublish(self):
        msg = msgpublish('ident', 'chan', 'somedata')
        assert msg == b'\x00\x00\x00\x18\x03\x05ident\x04chansomedata'

    def test_msgsubscribe(self):
        msg = msgsubscribe('ident', 'chan')
        assert msg == b'\x00\x00\x00\x0f\x04\x05identchan'

    def test_msgauth(self):
        msg = msgauth(b'rand', 'ident', 'secret')
        assert msg == (
            b'\x00\x00\x00\x1f\x02\x05ident\xbf\xa9^\x11I\xcd\x9es'
            b'\x80\xfd\xfcaJW\tZ\xb7\x19\xc1\xb4'
        )


class TestMessageReader(unittest.TestCase):

    def test_readinfo(self):
        name, rand = readinfo(b'\x07hpfeeds\x01 a\xff')
        assert name == 'hpfeeds'
        assert rand == b'\x01 a\xff'

    def test_readauth(self):
        ident, secret = readauth(
            b'\x05ident\xbf\xa9^\x11I\xcd\x9es'
            b'\x80\xfd\xfcaJW\tZ\xb7\x19\xc1\xb4'
        )
        assert ident == 'ident'
        assert secret == (
            b'\xbf\xa9^\x11I\xcd\x9es\x80\xfd\xfcaJW\tZ\xb7\x19\xc1\xb4'
        )

    def test_readpublish(self):
        ident, chan, data = readpublish(b'\x05ident\x04chansomedata')
        assert ident == 'ident'
        assert chan == 'chan'
        assert data == b'somedata'

    def test_readsubscribe(self):
        ident, chan = readsubscribe(b'\x05identchan')
        assert ident == 'ident'
        assert chan == 'chan'


class TestUnpacker(unittest.TestCase):

    def test_unpack_at_max_message_size_unicode_1(self):
        unpacker = Unpacker()
        data = msgpublish(b'b', b'a', u'\u2603'.encode('utf-8') * 349524)
        unpacker.feed(data)
        packets = list(iter(unpacker))
        assert len(unpacker.buf) == 0
        assert packets[0][0] == 3
        assert len(packets[0][1]) == (1024 ** 2)
        # assert packets[0][1].endswith(b'a' * 349525)

    def test_unpack_at_max_message_size_unicode_2(self):
        unpacker = Unpacker()
        unpacker.feed(msgpublish(b'', b'', u'\u001F'.encode('utf-8') * 1048574))
        packets = list(iter(unpacker))
        assert len(unpacker.buf) == 0
        assert packets[0][0] == 3
        assert len(packets[0][1]) == (1024 ** 2)
        # assert packets[0][1].endswith(b'a' * 349525)

    def test_unpack_at_max_message_size(self):
        unpacker = Unpacker()
        unpacker.feed(msgpublish(b'', b'', b'a' * 1048574))
        packets = list(iter(unpacker))
        assert len(unpacker.buf) == 0
        assert packets[0][0] == 3
        assert len(packets[0][1]) == (1024 ** 2)
        assert packets[0][1].endswith(b'a' * 1048574)

    def test_unpack_at_max_message_size_leftovers(self):
        unpacker = Unpacker()
        unpacker.feed(msgpublish(b'', b'', b'a' * 1048574) + b'z' * 1024)
        packets = [next(iter(unpacker))]
        assert len(unpacker.buf) == 1024
        assert packets[0][0] == 3
        # assert len(packets[0][1]) == (1024 ** 2)
        # assert packets[0][1].endswith(b'a' * 1048574)

    def test_unpack_1(self):
        unpacker = Unpacker()
        unpacker.feed(msghdr(1, b'abcdefghijklmnopqrstuvwxyz'))
        packets = list(iter(unpacker))
        assert packets == [(1, b'abcdefghijklmnopqrstuvwxyz')]

    def test_unpack_2(self):
        message = msghdr(1, b'abcdefghijklmnopqrstuvwxyz')
        unpacker = Unpacker()

        # The unpacker shouldn't yield any messages until it has consumed the
        # full object
        for b in message[:-1]:
            unpacker.feed([b])
            assert list(iter(unpacker)) == []

        unpacker.feed([message[-1]])
        assert list(iter(unpacker)) == [(1, b'abcdefghijklmnopqrstuvwxyz')]
