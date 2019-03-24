#!/usr/bin/env python

import logging
import optparse
import os
import string
import sys

import hpfeeds


def log(msg):
    print('[feedcli] {0}'.format(msg))


def on_message(ident, chan, payload):
    if [i for i in payload[:20] if i not in string.printable.encode('utf-8')]:
        payload = payload[:20].encode('hex') + '...'
    log('publish to {0} by {1}: {2}'.format(chan, ident, payload))


def _main(opts, action, pubdata=None):
    try:
        hpc = hpfeeds.new(
            opts.host,
            opts.port,
            opts.ident,
            opts.secret,
            certfile=opts.certfile,
        )
    except hpfeeds.FeedException as e:
        log('Error: {0}'.format(e))
        return 1

    def on_error(payload):
        log('Error message from broker: {0}'.format(payload))
        hpc.stop()

    log('connected to {0}'.format(hpc.brokername))

    if action == 'subscribe':
        hpc.subscribe(opts.channels)
        try:
            hpc.run(on_message, on_error)
        except hpfeeds.FeedException as e:
            log('Error: {0}'.format(e))
            return 1

    elif action == 'publish':
        hpc.publish(opts.channels, pubdata)
        emsg = hpc.wait()
        if emsg:
            print('got error from server:', emsg)

    elif action == 'sendfile':
        pubfile = open(pubdata, 'rb').read()
        hpc.publish(opts.channels, pubfile)

    log('closing connection.')
    hpc.close()

    return 0


def get_parser():
    parser = optparse.OptionParser()
    parser.add_option(
        "-c", "--chan",
        action="append", dest='channels', nargs=1, type='string',
        help="channel (can be used multiple times)")
    parser.add_option(
        "-i", "--ident",
        action="store", dest='ident', nargs=1, type='string',
        help="authkey identifier")
    parser.add_option(
        "-s", "--secret",
        action="store", dest='secret', nargs=1, type='string',
        help="authkey secret")
    parser.add_option(
        "--host",
        action="store", dest='host', nargs=1, type='string',
        help="broker host")
    parser.add_option(
        "-p", "--port",
        action="store", dest='port', nargs=1, type='int',
        help="broker port")
    parser.add_option(
        "-o", "--output",
        action="store", dest='output', nargs=1, type='string',
        help="publish log filename")
    parser.add_option(
        "--tlscert",
        action="store", dest='certfile', nargs=1, type='string',
        help="certfile for ssl verification (CA)", default=None)
    parser.add_option(
        "--debug",
        action="store_const", dest='debug',
        help="enable debug log output", default=False, const=True)

    return parser


def opts():
    parser = get_parser()

    options, args = parser.parse_args()

    if len(args) < 1:
        parser.error('You need to give "subscribe" or "publish" as <action>.')
    if args[0] not in ['subscribe', 'publish', 'sendfile']:
        parser.error('You need to give "subscribe" or "publish" as <action>.')

    logging.basicConfig(level=logging.DEBUG if options.debug else logging.CRITICAL)

    action = args[0]
    data = None
    if action == 'publish':
        data = ' '.join(args[1:])
    elif action == 'sendfile':
        data = ' '.join(args[1:])

    if options.certfile:
        if not os.path.exists(options.certfile):
            parser.error('If --tlscert is specified it must be a valid path to a file')

    if not options.host:
        parser.error('You must specify a host')

    if not options.port:
        parser.error('You must specify a port')

    if not options.ident:
        parser.error('You must specify an ident')

    if not options.secret:
        parser.error('You must specify a secret')

    return options, action, data


def main():
    options, action, data = opts()
    try:
        sys.exit(_main(options, action, pubdata=data))
    except KeyboardInterrupt:
        sys.exit(0)
