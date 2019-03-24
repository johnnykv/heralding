import select
import unittest

from hpfeeds.blocking.queue import Queue


class TestQueuePollable(unittest.TestCase):

    def test_write_queue(self):
        q = Queue()

        q.put_nowait('some data')

        # Queue has some data in - so should be readable
        r, w, x = select.select([q], [], [], 0)
        assert q in r

        # Queue still has data in, so still be readable
        r, w, x = select.select([q], [], [], 0)
        assert q in r

        assert q.get_nowait() == 'some data'

        # Queue has no data in, so no longer be readable
        r, w, x = select.select([q], [], [], 0)
        assert q not in r

    '''
    @mock.patch.object(os, 'name', new_callable=mock.PropertyMock)
    def test_fallback(self, os_name):
        os_name.return_value = 'nt'

        q = Queue()

        q.put_nowait('some data')

        # Queue has some data in - so should be readable
        r, w, x = select.select([q], [], [], 0)
        assert q in r

        # Queue still has data in, so still be readable
        r, w, x = select.select([q], [], [], 0)
        assert q in r

        assert q.get_nowait() == 'some data'

        # Queue has no data in, so no longer be readable
        r, w, x = select.select([q], [], [], 0)
        assert q not in r
    '''
