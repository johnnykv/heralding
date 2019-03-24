import os
import signal
import asyncio
import logging
import unittest

from aiosmtpd.handlers import Debugging
from aiosmtpd.main import main, parseargs
from aiosmtpd.smtp import SMTP, __version__
from contextlib import ExitStack
from functools import partial
from io import StringIO
from unittest.mock import patch

try:
    import pwd
except ImportError:
    pwd = None

has_setuid = hasattr(os, 'setuid')
log = logging.getLogger('mail.log')


class TestHandler1:
    def __init__(self, called):
        self.called = called

    @classmethod
    def from_cli(cls, parser, *args):
        return cls(*args)


class TestHandler2:
    pass


class TestMain(unittest.TestCase):
    def setUp(self):
        old_log_level = log.getEffectiveLevel()
        self.addCleanup(log.setLevel, old_log_level)
        self.resources = ExitStack()
        # Create a new event loop, and arrange for that loop to end almost
        # immediately.  This will allow the calls to main() in these tests to
        # also exit almost immediately.  Otherwise, the foreground test
        # process will hang.
        #
        # I think this introduces a race condition.  It depends on whether the
        # call_later() can possibly run before the run_forever() does, or could
        # cause it to not complete all its tasks.  In that case, you'd likely
        # get an error or warning on stderr, which may or may not cause the
        # test to fail.  I've only seen this happen once and don't have enough
        # information to know for sure.
        default_loop = asyncio.get_event_loop()
        loop = asyncio.new_event_loop()
        loop.call_later(0.1, loop.stop)
        self.resources.callback(asyncio.set_event_loop, default_loop)
        asyncio.set_event_loop(loop)
        self.addCleanup(self.resources.close)

    @unittest.skipIf(pwd is None, 'No pwd module available')
    def test_setuid(self):
        with patch('os.setuid') as mock:
            main(args=())
            mock.assert_called_with(pwd.getpwnam('nobody').pw_uid)

    @unittest.skipIf(pwd is None, 'No pwd module available')
    def test_setuid_permission_error(self):
        mock = self.resources.enter_context(
            patch('os.setuid', side_effect=PermissionError))
        stderr = StringIO()
        self.resources.enter_context(patch('sys.stderr', stderr))
        with self.assertRaises(SystemExit) as cm:
            main(args=())
        self.assertEqual(cm.exception.code, 1)
        mock.assert_called_with(pwd.getpwnam('nobody').pw_uid)
        self.assertEqual(
            stderr.getvalue(),
            'Cannot setuid "nobody"; try running with -n option.\n')

    @unittest.skipIf(pwd is None, 'No pwd module available')
    def test_setuid_no_pwd_module(self):
        self.resources.enter_context(patch('aiosmtpd.main.pwd', None))
        stderr = StringIO()
        self.resources.enter_context(patch('sys.stderr', stderr))
        with self.assertRaises(SystemExit) as cm:
            main(args=())
        self.assertEqual(cm.exception.code, 1)
        self.assertEqual(
            stderr.getvalue(),
            'Cannot import module "pwd"; try running with -n option.\n')

    @unittest.skipUnless(has_setuid, 'setuid is unvailable')
    def test_n(self):
        self.resources.enter_context(patch('aiosmtpd.main.pwd', None))
        self.resources.enter_context(
            patch('os.setuid', side_effect=PermissionError))
        # Just to short-circuit the main() function.
        self.resources.enter_context(
            patch('aiosmtpd.main.partial', side_effect=RuntimeError))
        # Getting the RuntimeError means that a SystemExit was never
        # triggered in the setuid section.
        self.assertRaises(RuntimeError, main, ('-n',))

    @unittest.skipUnless(has_setuid, 'setuid is unvailable')
    def test_nosetuid(self):
        self.resources.enter_context(patch('aiosmtpd.main.pwd', None))
        self.resources.enter_context(
            patch('os.setuid', side_effect=PermissionError))
        # Just to short-circuit the main() function.
        self.resources.enter_context(
            patch('aiosmtpd.main.partial', side_effect=RuntimeError))
        # Getting the RuntimeError means that a SystemExit was never
        # triggered in the setuid section.
        self.assertRaises(RuntimeError, main, ('--nosetuid',))

    def test_debug_0(self):
        # For this test, the runner will have already set the log level so it
        # may not be logging.ERROR.
        log = logging.getLogger('mail.log')
        default_level = log.getEffectiveLevel()
        with patch.object(log, 'info'):
            main(('-n',))
            self.assertEqual(log.getEffectiveLevel(), default_level)

    def test_debug_1(self):
        # Mock the logger to eliminate console noise.
        with patch.object(logging.getLogger('mail.log'), 'info'):
            main(('-n', '-d'))
            self.assertEqual(log.getEffectiveLevel(), logging.INFO)

    def test_debug_2(self):
        # Mock the logger to eliminate console noise.
        with patch.object(logging.getLogger('mail.log'), 'info'):
            main(('-n', '-dd'))
            self.assertEqual(log.getEffectiveLevel(), logging.DEBUG)

    def test_debug_3(self):
        # Mock the logger to eliminate console noise.
        with patch.object(logging.getLogger('mail.log'), 'info'):
            main(('-n', '-ddd'))
            self.assertEqual(log.getEffectiveLevel(), logging.DEBUG)
            self.assertTrue(asyncio.get_event_loop().get_debug())


class TestLoop(unittest.TestCase):
    def setUp(self):
        # We mock out so much of this, is it even worthwhile testing?  Well, it
        # does give us coverage.
        self.loop = asyncio.get_event_loop()
        pfunc = partial(patch.object, self.loop)
        resources = ExitStack()
        self.addCleanup(resources.close)
        self.create_server = resources.enter_context(pfunc('create_server'))
        self.run_until_complete = resources.enter_context(
            pfunc('run_until_complete'))
        self.add_signal_handler = resources.enter_context(
            pfunc('add_signal_handler'))
        resources.enter_context(
            patch.object(logging.getLogger('mail.log'), 'info'))
        self.run_forever = resources.enter_context(pfunc('run_forever'))

    def test_loop(self):
        main(('-n',))
        # create_server() is called with a partial as the factory, and a
        # socket object.
        self.assertEqual(self.create_server.call_count, 1)
        positional, keywords = self.create_server.call_args
        self.assertEqual(positional[0].func, SMTP)
        self.assertEqual(len(positional[0].args), 1)
        self.assertIsInstance(positional[0].args[0], Debugging)
        self.assertEqual(positional[0].keywords, dict(
            data_size_limit=None,
            enable_SMTPUTF8=False))
        self.assertEqual(sorted(keywords), ['host', 'port'])
        # run_until_complete() was called once.  The argument isn't important.
        self.assertTrue(self.run_until_complete.called)
        # add_signal_handler() is called with two arguments.
        self.assertEqual(self.add_signal_handler.call_count, 1)
        signal_number, callback = self.add_signal_handler.call_args[0]
        self.assertEqual(signal_number, signal.SIGINT)
        self.assertEqual(callback, self.loop.stop)
        # run_forever() was called once.
        self.assertEqual(self.run_forever.call_count, 1)

    def test_loop_keyboard_interrupt(self):
        # We mock out so much of this, is it even a worthwhile test?  Well, it
        # does give us coverage.
        self.run_forever.side_effect = KeyboardInterrupt
        main(('-n',))
        # loop.run_until_complete() was still executed.
        self.assertTrue(self.run_until_complete.called)

    def test_s(self):
        # We mock out so much of this, is it even a worthwhile test?  Well, it
        # does give us coverage.
        main(('-n', '-s', '3000'))
        positional, keywords = self.create_server.call_args
        self.assertEqual(positional[0].keywords, dict(
            data_size_limit=3000,
            enable_SMTPUTF8=False))

    def test_size(self):
        # We mock out so much of this, is it even a worthwhile test?  Well, it
        # does give us coverage.
        main(('-n', '--size', '3000'))
        positional, keywords = self.create_server.call_args
        self.assertEqual(positional[0].keywords, dict(
            data_size_limit=3000,
            enable_SMTPUTF8=False))

    def test_u(self):
        # We mock out so much of this, is it even a worthwhile test?  Well, it
        # does give us coverage.
        main(('-n', '-u'))
        positional, keywords = self.create_server.call_args
        self.assertEqual(positional[0].keywords, dict(
            data_size_limit=None,
            enable_SMTPUTF8=True))

    def test_smtputf8(self):
        # We mock out so much of this, is it even a worthwhile test?  Well, it
        # does give us coverage.
        main(('-n', '--smtputf8'))
        positional, keywords = self.create_server.call_args
        self.assertEqual(positional[0].keywords, dict(
            data_size_limit=None,
            enable_SMTPUTF8=True))


class TestParseArgs(unittest.TestCase):
    def test_handler_from_cli(self):
        # Ignore the host:port positional argument.
        parser, args = parseargs(
            ('-c', 'aiosmtpd.tests.test_main.TestHandler1', '--', 'FOO'))
        self.assertIsInstance(args.handler, TestHandler1)
        self.assertEqual(args.handler.called, 'FOO')

    def test_handler_no_from_cli(self):
        # Ignore the host:port positional argument.
        parser, args = parseargs(
            ('-c', 'aiosmtpd.tests.test_main.TestHandler2'))
        self.assertIsInstance(args.handler, TestHandler2)

    def test_handler_from_cli_exception(self):
        self.assertRaises(TypeError, parseargs,
                          ('-c', 'aiosmtpd.tests.test_main.TestHandler1',
                           'FOO', 'BAR'))

    def test_handler_no_from_cli_exception(self):
        stderr = StringIO()
        with patch('sys.stderr', stderr):
            with self.assertRaises(SystemExit) as cm:
                parseargs(
                    ('-c', 'aiosmtpd.tests.test_main.TestHandler2',
                     'FOO', 'BAR'))
            self.assertEqual(cm.exception.code, 2)
        usage_lines = stderr.getvalue().splitlines()
        self.assertEqual(
            usage_lines[-1][-57:],
            'Handler class aiosmtpd.tests.test_main takes no arguments')

    def test_default_host_port(self):
        parser, args = parseargs(args=())
        self.assertEqual(args.host, 'localhost')
        self.assertEqual(args.port, 8025)

    def test_l(self):
        parser, args = parseargs(args=('-l', 'foo:25'))
        self.assertEqual(args.host, 'foo')
        self.assertEqual(args.port, 25)

    def test_listen(self):
        parser, args = parseargs(args=('--listen', 'foo:25'))
        self.assertEqual(args.host, 'foo')
        self.assertEqual(args.port, 25)

    def test_host_no_port(self):
        parser, args = parseargs(args=('-l', 'foo'))
        self.assertEqual(args.host, 'foo')
        self.assertEqual(args.port, 8025)

    def test_host_no_host(self):
        parser, args = parseargs(args=('-l', ':25'))
        self.assertEqual(args.host, 'localhost')
        self.assertEqual(args.port, 25)

    def test_ipv6_host_port(self):
        parser, args = parseargs(args=('-l', '::0:25'))
        self.assertEqual(args.host, '::0')
        self.assertEqual(args.port, 25)

    def test_bad_port_number(self):
        stderr = StringIO()
        with patch('sys.stderr', stderr):
            with self.assertRaises(SystemExit) as cm:
                parseargs(('-l', ':foo'))
            self.assertEqual(cm.exception.code, 2)
        usage_lines = stderr.getvalue().splitlines()
        self.assertEqual(usage_lines[-1][-24:], 'Invalid port number: foo')

    def test_version(self):
        stdout = StringIO()
        with ExitStack() as resources:
            resources.enter_context(patch('sys.stdout', stdout))
            resources.enter_context(patch('aiosmtpd.main.PROGRAM', 'smtpd'))
            cm = resources.enter_context(self.assertRaises(SystemExit))
            parseargs(('--version',))
            self.assertEqual(cm.exception.code, 0)
        self.assertEqual(stdout.getvalue(), 'smtpd {}\n'.format(__version__))

    def test_v(self):
        stdout = StringIO()
        with ExitStack() as resources:
            resources.enter_context(patch('sys.stdout', stdout))
            resources.enter_context(patch('aiosmtpd.main.PROGRAM', 'smtpd'))
            cm = resources.enter_context(self.assertRaises(SystemExit))
            parseargs(('-v',))
            self.assertEqual(cm.exception.code, 0)
        self.assertEqual(stdout.getvalue(), 'smtpd {}\n'.format(__version__))
