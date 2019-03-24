==========
 aiosmtpd
==========

-----------------------------------------------------
Provide a Simple Mail Transfer Protocol (SMTP) server
-----------------------------------------------------

:Author: The aiosmtpd developers
:Date: 2017-07-01
:Copyright: 2015-2017 The aiosmtpd developers
:Version: 1.1
:Manual section: 1


SYNOPSIS
========

aiosmtpd [options]


Description
===========

This program provides an RFC 5321 compliant SMTP server that supports
customizable extensions.


OPTIONS
=======
-h, --help
    Show this help message and exit

-v, --version
    Show program's version number and exit.

-n, --nosetuid
    This program generally tries to setuid ``nobody``, unless this flag is
    set.  The setuid call will fail if this program is not run as root (in
    which case, use this flag).

-c CLASSPATH, --class CLASSPATH
    Use the given class (as a Python dotted import path) as the handler class
    for SMTP events.  This class can process received messages and do other
    actions during the SMTP dialog.  If not give, this uses a debugging
    handler by default.

    When given all remaining positional arguments are passed as arguments to
    the class's ``@classmethod from_cli()`` method, which should do any
    appropriate type conversion, and then return an instance of the handler
    class.

-s SIZE, --size SIZE
    Restrict the total size of the incoming message to SIZE number of bytes
    via the RFC 1870 SIZE extension.  Defaults to 33554432 bytes.

-u, --smtputf8
    Enable the SMTPUTF8 extension and behave as an RFC 6531 SMTP proxy.

-d, --debug
    Increase debugging output.

-l [HOST:PORT], --listen [HOST:PORT]
    Optional host and port to listen on. If the PORT part is not given, then
    port 8025 is used. If only :PORT is given, then localhost is used for the
    hostname. If neither are given, localhost:8025 is used.
