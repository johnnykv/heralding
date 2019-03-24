.. _cli:

====================
 Command line usage
====================

``aiosmtpd`` provides a main entry point which can be used to run the server
on the command line.  There are two ways to run the server, depending on how
the package has been installed.

You can run the server by passing it to Python directly::

    $ python3 -m aiosmtpd -n

This starts a server on localhost, port 8025 without setting the uid to
'nobody' (i.e. because you aren't running it as root).  Once you've done that,
you can connect directly to the server using your favorite command line
protocol tool.  Type the ``QUIT`` command at the server once you see the
greeting::

    % telnet localhost 8025
    Trying 127.0.0.1...
    Connected to localhost.
    Escape character is '^]'.
    220 subdivisions Python SMTP ...
    QUIT
    221 Bye
    Connection closed by foreign host.

Of course, you could use Python's smtplib_ module, or any other SMTP client to
talk to the server.

Hit control-C at the server to stop it.

The entry point may also be installed as the ``aiosmtpd`` command, so this is
equivalent to the above ``python3`` invocation::

    $ aiosmtpd -n


Options
=======

Optional arguments include:

``-h``, ``--help``
    Show this help message and exit.

``-n``, ``--nosetuid``
    This program generally tries to setuid ``nobody``, unless this flag is
    set.  The setuid call will fail if this program is not run as root (in
    which case, use this flag).

``-c CLASSPATH``, ``--class CLASSPATH``
    Use the given class, as a Python dotted import path, as the :ref:`handler
    class <handlers>` for SMTP events.  This class can process received
    messages and do other actions during the SMTP dialog.  Uses a debugging
    handler by default.

``-s SIZE``, ``--size SIZE``
    Restrict the total size of the incoming message to ``SIZE`` number of
    bytes via the `RFC 1870`_ ``SIZE`` extension.  Defaults to 33554432 bytes.

``-u``, ``--smtputf8``
    Enable the SMTPUTF8 extension and behave as an `RFC 6531`_ SMTP proxy.

``-d``, ``--debug``
    Increase debugging output.

``-l [HOST:PORT]``, ``--listen [HOST:PORT]``
    Optional host and port to listen on.  If the ``PORT`` part is not given,
    then port 8025 is used.  If only ``:PORT`` is given, then ``localhost`` is
    used for the host name.  If neither are given, ``localhost:8025`` is used.

Optional positional arguments provide additional arguments to the handler
class constructor named in the ``--class`` option.  Provide as many of these
as supported by the handler class's ``from_cli()`` class method, if provided.


.. _smtplib: https://docs.python.org/3/library/smtplib.html
.. _`RFC 1870`: http://www.faqs.org/rfcs/rfc1870.html
.. _`RFC 6531`: http://www.faqs.org/rfcs/rfc6531.html
