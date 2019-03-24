import os
import sys
import signal
import asyncio
import logging

from aiosmtpd.smtp import DATA_SIZE_DEFAULT, SMTP, __version__
from argparse import ArgumentParser
from contextlib import suppress
from functools import partial
from importlib import import_module
from public import public

try:
    import pwd
except ImportError:                                         # pragma: nocover
    pwd = None


DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 8025

# Make the program name a little nicer, especially when `python3 -m aiosmtpd`
# is used.
PROGRAM = 'smtpd' if '__main__.py' in sys.argv[0] else sys.argv[0]


def parseargs(args=None):
    parser = ArgumentParser(
        prog=PROGRAM,
        description='An RFC 5321 SMTP server with extensions.')
    parser.add_argument(
        '-v', '--version', action='version',
        version='%(prog)s {}'.format(__version__))
    parser.add_argument(
        '-n', '--nosetuid',
        dest='setuid', default=True, action='store_false',
        help="""This program generally tries to setuid `nobody`, unless this
                flag is set.  The setuid call will fail if this program is not
                run as root (in which case, use this flag).""")
    parser.add_argument(
        '-c', '--class',
        dest='classpath',
        default='aiosmtpd.handlers.Debugging',
        help="""Use the given class, as a Python dotted import path, as the
                handler class for SMTP events.  This class can process
                received messages and do other actions during the SMTP
                dialog.  Uses a debugging handler by default.""")
    parser.add_argument(
        '-s', '--size',
        type=int,
        help="""Restrict the total size of the incoming message to
                SIZE number of bytes via the RFC 1870 SIZE extension.
                Defaults to {} bytes.""".format(DATA_SIZE_DEFAULT))
    parser.add_argument(
        '-u', '--smtputf8',
        default=False, action='store_true',
        help="""Enable the SMTPUTF8 extension and behave as an RFC 6531
                SMTP proxy.""")
    parser.add_argument(
        '-d', '--debug',
        default=0, action='count',
        help="""Increase debugging output.""")
    parser.add_argument(
        '-l', '--listen', metavar='HOST:PORT',
        nargs='?', default=None,
        help="""Optional host and port to listen on.  If the PORT part is not
                given, then port {port} is used.  If only :PORT is given,
                then {host} is used for the hostname.  If neither are given,
                {host}:{port} is used.""".format(
                    host=DEFAULT_HOST, port=DEFAULT_PORT))
    parser.add_argument(
        'classargs', metavar='CLASSARGS',
        nargs='*', default=(),
        help="""Additional arguments passed to the handler CLASS.""")
    args = parser.parse_args(args)
    # Find the handler class.
    path, dot, name = args.classpath.rpartition('.')
    module = import_module(path)
    handler_class = getattr(module, name)
    if hasattr(handler_class, 'from_cli'):
        args.handler = handler_class.from_cli(parser, *args.classargs)
    else:
        if len(args.classargs) > 0:
            parser.error('Handler class {} takes no arguments'.format(path))
        args.handler = handler_class()
    # Parse the host:port argument.
    if args.listen is None:
        args.host = DEFAULT_HOST
        args.port = DEFAULT_PORT
    else:
        host, colon, port = args.listen.rpartition(':')
        if len(colon) == 0:
            args.host = port
            args.port = DEFAULT_PORT
        else:
            args.host = DEFAULT_HOST if len(host) == 0 else host
            try:
                args.port = int(DEFAULT_PORT if len(port) == 0 else port)
            except ValueError:
                parser.error('Invalid port number: {}'.format(port))
    return parser, args


@public
def main(args=None):
    parser, args = parseargs(args=args)

    if args.setuid:                               # pragma: nomswin
        if pwd is None:
            print('Cannot import module "pwd"; try running with -n option.',
                  file=sys.stderr)
            sys.exit(1)
        nobody = pwd.getpwnam('nobody').pw_uid
        try:
            os.setuid(nobody)
        except PermissionError:
            print('Cannot setuid "nobody"; try running with -n option.',
                  file=sys.stderr)
            sys.exit(1)

    factory = partial(
        SMTP, args.handler,
        data_size_limit=args.size, enable_SMTPUTF8=args.smtputf8)

    logging.basicConfig(level=logging.ERROR)
    log = logging.getLogger('mail.log')
    loop = asyncio.get_event_loop()

    if args.debug > 0:
        log.setLevel(logging.INFO)
    if args.debug > 1:
        log.setLevel(logging.DEBUG)
    if args.debug > 2:
        loop.set_debug(enabled=True)

    log.info('Server listening on %s:%s', args.host, args.port)

    server = loop.run_until_complete(
        loop.create_server(factory, host=args.host, port=args.port))
    # Signal handlers are only supported on *nix, so just ignore the failure
    # to set this on Windows.
    with suppress(NotImplementedError):
        loop.add_signal_handler(signal.SIGINT, loop.stop)

    log.info('Starting asyncio loop')
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    server.close()
    log.info('Completed asyncio loop')
    loop.run_until_complete(server.wait_closed())
    loop.close()


if __name__ == '__main__':                          # pragma: nocover
    main()
