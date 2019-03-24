import os
import sys
import unittest

from aiosmtpd.controller import Controller
from aiosmtpd.handlers import AsyncMessage, Debugging, Mailbox, Proxy, Sink
from aiosmtpd.smtp import SMTP as Server
from contextlib import ExitStack
from io import StringIO
from mailbox import Maildir
from operator import itemgetter
from smtplib import SMTP, SMTPDataError, SMTPRecipientsRefused
from tempfile import TemporaryDirectory
from unittest.mock import call, patch


CRLF = '\r\n'


class DecodingController(Controller):
    def factory(self):
        return Server(self.handler, decode_data=True)


class DataHandler:
    def __init__(self):
        self.content = None
        self.original_content = None

    async def handle_DATA(self, server, session, envelope):
        self.content = envelope.content
        self.original_content = envelope.original_content
        return '250 OK'


class TestDebugging(unittest.TestCase):
    def setUp(self):
        self.stream = StringIO()
        handler = Debugging(self.stream)
        controller = DecodingController(handler)
        controller.start()
        self.addCleanup(controller.stop)
        self.address = (controller.hostname, controller.port)

    def test_debugging(self):
        with ExitStack() as resources:
            client = resources.enter_context(SMTP(*self.address))
            peer = client.sock.getsockname()
            client.sendmail('anne@example.com', ['bart@example.com'], """\
From: Anne Person <anne@example.com>
To: Bart Person <bart@example.com>
Subject: A test

Testing
""")
        text = self.stream.getvalue()
        self.assertMultiLineEqual(text, """\
---------- MESSAGE FOLLOWS ----------
mail options: ['SIZE=102']

From: Anne Person <anne@example.com>
To: Bart Person <bart@example.com>
Subject: A test
X-Peer: {!r}

Testing
------------ END MESSAGE ------------
""".format(peer))


class TestDebuggingBytes(unittest.TestCase):
    def setUp(self):
        self.stream = StringIO()
        handler = Debugging(self.stream)
        controller = Controller(handler)
        controller.start()
        self.addCleanup(controller.stop)
        self.address = (controller.hostname, controller.port)

    def test_debugging(self):
        with ExitStack() as resources:
            client = resources.enter_context(SMTP(*self.address))
            peer = client.sock.getsockname()
            client.sendmail('anne@example.com', ['bart@example.com'], """\
From: Anne Person <anne@example.com>
To: Bart Person <bart@example.com>
Subject: A test

Testing
""")
        text = self.stream.getvalue()
        self.assertMultiLineEqual(text, """\
---------- MESSAGE FOLLOWS ----------
mail options: ['SIZE=102']

From: Anne Person <anne@example.com>
To: Bart Person <bart@example.com>
Subject: A test
X-Peer: {!r}

Testing
------------ END MESSAGE ------------
""".format(peer))


class TestDebuggingOptions(unittest.TestCase):
    def setUp(self):
        self.stream = StringIO()
        handler = Debugging(self.stream)
        controller = Controller(handler)
        controller.start()
        self.addCleanup(controller.stop)
        self.address = (controller.hostname, controller.port)

    def test_debugging_without_options(self):
        with SMTP(*self.address) as client:
            # Prevent ESMTP options.
            client.helo()
            peer = client.sock.getsockname()
            client.sendmail('anne@example.com', ['bart@example.com'], """\
From: Anne Person <anne@example.com>
To: Bart Person <bart@example.com>
Subject: A test

Testing
""")
        text = self.stream.getvalue()
        self.assertMultiLineEqual(text, """\
---------- MESSAGE FOLLOWS ----------
From: Anne Person <anne@example.com>
To: Bart Person <bart@example.com>
Subject: A test
X-Peer: {!r}

Testing
------------ END MESSAGE ------------
""".format(peer))

    def test_debugging_with_options(self):
        with SMTP(*self.address) as client:
            peer = client.sock.getsockname()
            client.sendmail('anne@example.com', ['bart@example.com'], """\
From: Anne Person <anne@example.com>
To: Bart Person <bart@example.com>
Subject: A test

Testing
""", mail_options=['BODY=7BIT'])
        text = self.stream.getvalue()
        self.assertMultiLineEqual(text, """\
---------- MESSAGE FOLLOWS ----------
mail options: ['SIZE=102', 'BODY=7BIT']

From: Anne Person <anne@example.com>
To: Bart Person <bart@example.com>
Subject: A test
X-Peer: {!r}

Testing
------------ END MESSAGE ------------
""".format(peer))


class TestMessage(unittest.TestCase):
    def test_message(self):
        # In this test, the message content comes in as a bytes.
        handler = DataHandler()
        controller = Controller(handler)
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            client.sendmail('anne@example.com', ['bart@example.com'], """\
From: Anne Person <anne@example.com>
To: Bart Person <bart@example.com>
Subject: A test
Message-ID: <ant>

Testing
""")
        # The content is not converted, so it's bytes.
        self.assertEqual(handler.content, handler.original_content)
        self.assertIsInstance(handler.content, bytes)
        self.assertIsInstance(handler.original_content, bytes)

    def test_message_decoded(self):
        # In this test, the message content comes in as a string.
        handler = DataHandler()
        controller = DecodingController(handler)
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            client.sendmail('anne@example.com', ['bart@example.com'], """\
From: Anne Person <anne@example.com>
To: Bart Person <bart@example.com>
Subject: A test
Message-ID: <ant>

Testing
""")
        self.assertNotEqual(handler.content, handler.original_content)
        self.assertIsInstance(handler.content, str)
        self.assertIsInstance(handler.original_content, bytes)


class TestAsyncMessage(unittest.TestCase):
    def setUp(self):
        self.handled_message = None

        class MessageHandler(AsyncMessage):
            async def handle_message(handler_self, message):
                self.handled_message = message

        self.handler = MessageHandler()

    def test_message(self):
        # In this test, the message data comes in as bytes.
        controller = Controller(self.handler)
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            client.sendmail('anne@example.com', ['bart@example.com'], """\
From: Anne Person <anne@example.com>
To: Bart Person <bart@example.com>
Subject: A test
Message-ID: <ant>

Testing
""")
        self.assertEqual(self.handled_message['subject'], 'A test')
        self.assertEqual(self.handled_message['message-id'], '<ant>')
        self.assertIsNotNone(self.handled_message['X-Peer'])
        self.assertEqual(
            self.handled_message['X-MailFrom'], 'anne@example.com')
        self.assertEqual(self.handled_message['X-RcptTo'], 'bart@example.com')

    def test_message_decoded(self):
        # With a server that decodes the data, the messages come in as
        # strings.  There's no difference in the message seen by the
        # handler's handle_message() method, but internally this gives full
        # coverage.
        controller = DecodingController(self.handler)
        controller.start()
        self.addCleanup(controller.stop)

        with SMTP(controller.hostname, controller.port) as client:
            client.sendmail('anne@example.com', ['bart@example.com'], """\
From: Anne Person <anne@example.com>
To: Bart Person <bart@example.com>
Subject: A test
Message-ID: <ant>

Testing
""")
        self.assertEqual(self.handled_message['subject'], 'A test')
        self.assertEqual(self.handled_message['message-id'], '<ant>')
        self.assertIsNotNone(self.handled_message['X-Peer'])
        self.assertEqual(
            self.handled_message['X-MailFrom'], 'anne@example.com')
        self.assertEqual(self.handled_message['X-RcptTo'], 'bart@example.com')


class TestMailbox(unittest.TestCase):
    def setUp(self):
        self.tempdir = TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.maildir_path = os.path.join(self.tempdir.name, 'maildir')
        self.handler = handler = Mailbox(self.maildir_path)
        controller = Controller(handler)
        controller.start()
        self.addCleanup(controller.stop)
        self.address = (controller.hostname, controller.port)

    def test_mailbox(self):
        with SMTP(*self.address) as client:
            client.sendmail(
                'aperson@example.com', ['bperson@example.com'], """\
From: Anne Person <anne@example.com>
To: Bart Person <bart@example.com>
Subject: A test
Message-ID: <ant>

Hi Bart, this is Anne.
""")
            client.sendmail(
                'cperson@example.com', ['dperson@example.com'], """\
From: Cate Person <cate@example.com>
To: Dave Person <dave@example.com>
Subject: A test
Message-ID: <bee>

Hi Dave, this is Cate.
""")
            client.sendmail(
                'eperson@example.com', ['fperson@example.com'], """\
From: Elle Person <elle@example.com>
To: Fred Person <fred@example.com>
Subject: A test
Message-ID: <cat>

Hi Fred, this is Elle.
""")
        # Check the messages in the mailbox.
        mailbox = Maildir(self.maildir_path)
        messages = sorted(mailbox, key=itemgetter('message-id'))
        self.assertEqual(
            list(message['message-id'] for message in messages),
            ['<ant>', '<bee>', '<cat>'])

    def test_mailbox_reset(self):
        with SMTP(*self.address) as client:
            client.sendmail(
                'aperson@example.com', ['bperson@example.com'], """\
From: Anne Person <anne@example.com>
To: Bart Person <bart@example.com>
Subject: A test
Message-ID: <ant>

Hi Bart, this is Anne.
""")
        self.handler.reset()
        mailbox = Maildir(self.maildir_path)
        self.assertEqual(list(mailbox), [])


class FakeParser:
    def __init__(self):
        self.message = None

    def error(self, message):
        self.message = message
        raise SystemExit


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.parser = FakeParser()

    def test_debugging_cli_no_args(self):
        handler = Debugging.from_cli(self.parser)
        self.assertIsNone(self.parser.message)
        self.assertEqual(handler.stream, sys.stdout)

    def test_debugging_cli_two_args(self):
        self.assertRaises(
            SystemExit,
            Debugging.from_cli, self.parser, 'foo', 'bar')
        self.assertEqual(
            self.parser.message, 'Debugging usage: [stdout|stderr]')

    def test_debugging_cli_stdout(self):
        handler = Debugging.from_cli(self.parser, 'stdout')
        self.assertIsNone(self.parser.message)
        self.assertEqual(handler.stream, sys.stdout)

    def test_debugging_cli_stderr(self):
        handler = Debugging.from_cli(self.parser, 'stderr')
        self.assertIsNone(self.parser.message)
        self.assertEqual(handler.stream, sys.stderr)

    def test_debugging_cli_bad_argument(self):
        self.assertRaises(
            SystemExit,
            Debugging.from_cli, self.parser, 'stdfoo')
        self.assertEqual(
            self.parser.message, 'Debugging usage: [stdout|stderr]')

    def test_sink_cli_no_args(self):
        handler = Sink.from_cli(self.parser)
        self.assertIsNone(self.parser.message)
        self.assertIsInstance(handler, Sink)

    def test_sink_cli_any_args(self):
        self.assertRaises(
            SystemExit,
            Sink.from_cli, self.parser, 'foo')
        self.assertEqual(
            self.parser.message, 'Sink handler does not accept arguments')

    def test_mailbox_cli_no_args(self):
        self.assertRaises(SystemExit, Mailbox.from_cli, self.parser)
        self.assertEqual(
            self.parser.message,
            'The directory for the maildir is required')

    def test_mailbox_cli_too_many_args(self):
        self.assertRaises(SystemExit, Mailbox.from_cli, self.parser,
                          'foo', 'bar', 'baz')
        self.assertEqual(
            self.parser.message,
            'Too many arguments for Mailbox handler')

    def test_mailbox_cli(self):
        with TemporaryDirectory() as tmpdir:
            handler = Mailbox.from_cli(self.parser, tmpdir)
            self.assertIsInstance(handler.mailbox, Maildir)
            self.assertEqual(handler.mail_dir, tmpdir)


class TestProxy(unittest.TestCase):
    def setUp(self):
        # There are two controllers and two SMTPd's running here.  The
        # "upstream" one listens on port 9025 and is connected to a "data
        # handler" which captures the messages it receives.  The second -and
        # the one under test here- listens on port 9024 and proxies to the one
        # on port 9025.  Because we need to set the decode_data flag
        # differently for each different test, the controller of the proxy is
        # created in the individual tests, not in the setup.
        self.upstream = DataHandler()
        upstream_controller = Controller(self.upstream, port=9025)
        upstream_controller.start()
        self.addCleanup(upstream_controller.stop)
        self.proxy = Proxy(upstream_controller.hostname, 9025)
        self.source = """\
From: Anne Person <anne@example.com>
To: Bart Person <bart@example.com>
Subject: A test

Testing
"""
        # The upstream SMTPd will always receive the content as bytes
        # delimited with CRLF.
        self.expected = CRLF.join([
            'From: Anne Person <anne@example.com>',
            'To: Bart Person <bart@example.com>',
            'Subject: A test',
            'X-Peer: ::1',
            '',
            'Testing']).encode('ascii')

    def test_deliver_bytes(self):
        with ExitStack() as resources:
            controller = Controller(self.proxy, port=9024)
            controller.start()
            resources.callback(controller.stop)
            client = resources.enter_context(
                SMTP(*(controller.hostname, controller.port)))
            client.sendmail(
                'anne@example.com', ['bart@example.com'], self.source)
            client.quit()
        self.assertEqual(self.upstream.content, self.expected)
        self.assertEqual(self.upstream.original_content, self.expected)

    def test_deliver_str(self):
        with ExitStack() as resources:
            controller = DecodingController(self.proxy, port=9024)
            controller.start()
            resources.callback(controller.stop)
            client = resources.enter_context(
                SMTP(*(controller.hostname, controller.port)))
            client.sendmail(
                'anne@example.com', ['bart@example.com'], self.source)
            client.quit()
        self.assertEqual(self.upstream.content, self.expected)
        self.assertEqual(self.upstream.original_content, self.expected)


class TestProxyMocked(unittest.TestCase):
    def setUp(self):
        handler = Proxy('localhost', 9025)
        controller = DecodingController(handler)
        controller.start()
        self.addCleanup(controller.stop)
        self.address = (controller.hostname, controller.port)
        self.source = """\
From: Anne Person <anne@example.com>
To: Bart Person <bart@example.com>
Subject: A test

Testing
"""

    def test_recipients_refused(self):
        with ExitStack() as resources:
            log_mock = resources.enter_context(patch('aiosmtpd.handlers.log'))
            mock = resources.enter_context(
                patch('aiosmtpd.handlers.smtplib.SMTP'))
            mock().sendmail.side_effect = SMTPRecipientsRefused({
                'bart@example.com': (500, 'Bad Bart'),
                })
            client = resources.enter_context(SMTP(*self.address))
            client.sendmail(
                'anne@example.com', ['bart@example.com'], self.source)
            client.quit()
            # The log contains information about what happened in the proxy.
            self.assertEqual(
                log_mock.info.call_args_list, [
                    call('got SMTPRecipientsRefused'),
                    call('we got some refusals: %s',
                         {'bart@example.com': (500, 'Bad Bart')})]
                )

    def test_oserror(self):
        with ExitStack() as resources:
            log_mock = resources.enter_context(patch('aiosmtpd.handlers.log'))
            mock = resources.enter_context(
                patch('aiosmtpd.handlers.smtplib.SMTP'))
            mock().sendmail.side_effect = OSError
            client = resources.enter_context(SMTP(*self.address))
            client.sendmail(
                'anne@example.com', ['bart@example.com'], self.source)
            client.quit()
            # The log contains information about what happened in the proxy.
            self.assertEqual(
                log_mock.info.call_args_list, [
                    call('we got some refusals: %s',
                         {'bart@example.com': (-1, 'ignore')}),
                    ]
                )


class HELOHandler:
    async def handle_HELO(self, server, session, envelope, hostname):
        return '250 geddy.example.com'


class EHLOHandler:
    async def handle_EHLO(self, server, session, envelope, hostname):
        return '250 alex.example.com'


class MAILHandler:
    async def handle_MAIL(self, server, session, envelope, address, options):
        envelope.mail_options.extend(options)
        return '250 Yeah, sure'


class RCPTHandler:
    async def handle_RCPT(self, server, session, envelope, address, options):
        envelope.rcpt_options.extend(options)
        if address == 'bart@example.com':
            return '550 Rejected'
        envelope.rcpt_tos.append(address)
        return '250 OK'


class DATAHandler:
    async def handle_DATA(self, server, session, envelope):
        return '599 Not today'


class NoHooksHandler:
    pass


class TestHooks(unittest.TestCase):
    def test_rcpt_hook(self):
        controller = Controller(RCPTHandler())
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            with self.assertRaises(SMTPRecipientsRefused) as cm:
                client.sendmail('anne@example.com', ['bart@example.com'], """\
From: anne@example.com
To: bart@example.com
Subject: Test

""")
            self.assertEqual(cm.exception.recipients, {
                'bart@example.com': (550, b'Rejected'),
                })

    def test_helo_hook(self):
        controller = Controller(HELOHandler())
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            code, response = client.helo('me')
        self.assertEqual(code, 250)
        self.assertEqual(response, b'geddy.example.com')

    def test_ehlo_hook(self):
        controller = Controller(EHLOHandler())
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            code, response = client.ehlo('me')
        self.assertEqual(code, 250)
        lines = response.decode('utf-8').splitlines()
        self.assertEqual(lines[-1], 'alex.example.com')

    def test_mail_hook(self):
        controller = Controller(MAILHandler())
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            client.helo('me')
            code, response = client.mail('anne@example.com')
        self.assertEqual(code, 250)
        self.assertEqual(response, b'Yeah, sure')

    def test_data_hook(self):
        controller = Controller(DATAHandler())
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            with self.assertRaises(SMTPDataError) as cm:
                client.sendmail('anne@example.com', ['bart@example.com'], """\
From: anne@example.com
To: bart@example.com
Subject: Test

Yikes
""")
            self.assertEqual(cm.exception.smtp_code, 599)
            self.assertEqual(cm.exception.smtp_error, b'Not today')

    def test_no_hooks(self):
        controller = Controller(NoHooksHandler())
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            client.helo('me')
            client.mail('anne@example.com')
            client.rcpt(['bart@example.com'])
            code, response = client.data("""\
From: anne@example.com
To: bart@example.com
Subject: Test

""")
            self.assertEqual(code, 250)


class CapturingServer(Server):
    def __init__(self, *args, **kws):
        self.warnings = None
        super().__init__(*args, **kws)

    async def smtp_DATA(self, arg):
        with patch('aiosmtpd.smtp.warn') as mock:
            await super().smtp_DATA(arg)
        self.warnings = mock.call_args_list


class CapturingController(Controller):
    def factory(self):
        self.smtpd = CapturingServer(self.handler)
        return self.smtpd


class DeprecatedHandler:
    def process_message(self, peer, mailfrom, rcpttos, data, **kws):
        pass


class AsyncDeprecatedHandler:
    async def process_message(self, peer, mailfrom, rcpttos, data, **kws):
        pass


class DeprecatedHookServer(Server):
    def __init__(self, *args, **kws):
        self.warnings = None
        super().__init__(*args, **kws)

    async def smtp_EHLO(self, arg):
        with patch('aiosmtpd.smtp.warn') as mock:
            await super().smtp_EHLO(arg)
        self.warnings = mock.call_args_list

    async def smtp_RSET(self, arg):
        with patch('aiosmtpd.smtp.warn') as mock:
            await super().smtp_RSET(arg)
        self.warnings = mock.call_args_list

    async def ehlo_hook(self):
        pass

    async def rset_hook(self):
        pass


class DeprecatedHookController(Controller):
    def factory(self):
        self.smtpd = DeprecatedHookServer(self.handler)
        return self.smtpd


class TestDeprecation(unittest.TestCase):
    # handler.process_message() is deprecated.
    def test_deprecation(self):
        controller = CapturingController(DeprecatedHandler())
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            client.sendmail('anne@example.com', ['bart@example.com'], """\
From: Anne Person <anne@example.com>
To: Bart Person <bart@example.com>
Subject: A test

Testing
""")
        self.assertEqual(len(controller.smtpd.warnings), 1)
        self.assertEqual(
            controller.smtpd.warnings[0],
            call('Use handler.handle_DATA() instead of .process_message()',
                 DeprecationWarning))

    def test_deprecation_async(self):
        controller = CapturingController(AsyncDeprecatedHandler())
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            client.sendmail('anne@example.com', ['bart@example.com'], """\
From: Anne Person <anne@example.com>
To: Bart Person <bart@example.com>
Subject: A test

Testing
""")
        self.assertEqual(len(controller.smtpd.warnings), 1)
        self.assertEqual(
            controller.smtpd.warnings[0],
            call('Use handler.handle_DATA() instead of .process_message()',
                 DeprecationWarning))

    def test_ehlo_hook_deprecation(self):
        controller = DeprecatedHookController(Sink())
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            client.ehlo('example.com')
        self.assertEqual(len(controller.smtpd.warnings), 1)
        self.assertEqual(
            controller.smtpd.warnings[0],
            call('Use handler.handle_EHLO() instead of .ehlo_hook()',
                 DeprecationWarning))

    def test_rset_hook_deprecation(self):
        controller = DeprecatedHookController(Sink())
        controller.start()
        self.addCleanup(controller.stop)
        with SMTP(controller.hostname, controller.port) as client:
            client.rset()
        self.assertEqual(len(controller.smtpd.warnings), 1)
        self.assertEqual(
            controller.smtpd.warnings[0],
            call('Use handler.handle_RSET() instead of .rset_hook()',
                 DeprecationWarning))
