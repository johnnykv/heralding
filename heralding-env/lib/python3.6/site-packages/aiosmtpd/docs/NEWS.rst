===================
 NEWS for aiosmtpd
===================

1.2 (2018-09-01)
================
* Improve the documentation on enabling ``STARTTLS``.  (Closes #125)
* Add customizable ident field to SMTP class constructor. (Closes #131)
* Remove asyncio.coroutine decorator as it was introduced in Python 3.5.
* Add Controller docstring, explain dual-stack binding. (Closes #140)
* Gracefully handle ASCII decoding exceptions. (Closes #142)
* Fix typo.
* Improve Controller ssl_context documentation.
* Add timeout feature. (Partial fix for #145)


1.1 (2017-07-06)
================
* Drop support for Python 3.4.
* As per RFC 5321, §4.1.4, multiple ``HELO`` / ``EHLO`` commands in the same
  session are semantically equivalent to ``RSET``.  (Closes #78)
* As per RFC 5321, $4.1.1.9, ``NOOP`` takes an optional argument, which is
  ignored.  **API BREAK** If you have a handler that implements
  ``handle_NOOP()``, it previously took zero arguments but now requires a
  single argument.  (Closes #107)
* The command line options ``--version`` / ``-v`` has been added to print the
  package's current version number.  (Closes #111)
* General improvements in the ``Controller`` class.  (Closes #104)
* When aiosmtpd handles a ``STARTTLS`` it must arrange for the original
  transport to be closed when the wrapped transport is closed.  This fixes a
  hidden exception which occurs when an EOF is received on the original
  tranport after the connection is lost.  (Closes #83)
* Widen the catch of ``ConnectionResetError`` and ``CancelledError`` to also
  catch such errors from handler methods.  (Closes #110)
* Added a manpage for the ``aiosmtpd`` command line script.  (Closes #116)
* Added much better support for the ``HELP``.  There's a new decorator called
  ``@syntax()`` which you can use in derived classes to decorate ``smtp_*()``
  methods.  These then show up in ``HELP`` responses.  This also fixes
  ``HELP`` responses for the ``LMTP`` subclass.  (Closes #113)
* The ``Controller`` class now takes an optional keyword argument
  ``ssl_context`` which is passed directly to the asyncio ``create_server()``
  call.

1.0 (2017-05-15)
================
* Release.

1.0rc1 (2017-05-12)
===================
* Improved documentation.

1.0b1 (2017-05-07)
==================
* The connection peer is displayed in all INFO level logging.
* When running the test suite, you can include a ``-E`` option after the
  ``--`` separator to boost the debugging output.
* The main SMTP readline loops are now more robust against connection resets
  and mid-read EOFs.  (Closes #62)
* ``Proxy`` handlers work with ``SMTP`` servers regardless of the value of the
  ``decode_data`` argument.
* The command line script is now installed as ``aiosmtpd`` instead of
  ``smtpd``.
* The ``SMTP`` class now does a better job of handling Unicode, when the
  client does not claim to support ``SMTPUTF8`` but sends non-ASCII anyway.
  The server forces ASCII-only handling when ``enable_SMTPUTF8=False`` (the
  default) is passed to the constructor.  The command line arguments
  ``decode_data=True`` and ``enable_SMTPUTF8=True`` are no longer mutually
  exclusive.
* Officially support Windows.  (Closes #76)

1.0a5 (2017-04-06)
==================
* A new handler hook API has been added which provides more flexibility but
  requires more responsibility (e.g. hooks must return a string status).
  Deprecate ``SMTP.ehlo_hook()`` and ``SMTP.rset_hook()``.
* Deprecate handler ``process_message()`` methods.  Use the new asynchronous
  ``handle_DATA()`` methods, which take a session and an envelope object.
* Added the ``STARTTLS`` extension.  Given by Konstantin Volkov.
* Minor changes to the way the ``Debugging`` handler prints ``mail_options``
  and ``rcpt_options`` (although the latter is still not support in ``SMTP``).
* ``DATA`` method now respects original line endings, and passing size limits
  is now handled better.  Given by Konstantin Volkov.
* The ``Controller`` class has two new optional keyword arguments.

  - ``ready_timeout`` specifies a timeout in seconds that can be used to limit
    the amount of time it waits for the server to become ready.  This can also
    be overridden with the environment variable
    ``AIOSMTPD_CONTROLLER_TIMEOUT``. (Closes #35)
  - ``enable_SMTPUTF8`` is passed through to the ``SMTP`` constructor in the
    default factory.  If you override ``Controller.factory()`` you can pass
    ``self.enable_SMTPUTF8`` yourself.
* Handlers can define a ``handle_tls_handshake()`` method, which takes a
  session object, and is called if SSL is enabled during the making of the
  connection.  (Closes #48)
* Better Windows compatibility.
* Better Python 3.4 compatibility.
* Use ``flufl.testing`` package for nose2 and flake8 plugins.
* The test suite has achieved 100% code coverage. (Closes #2)

1.0a4 (2016-11-29)
==================
* The SMTP server connection identifier can be changed by setting the
  ``__ident__`` attribute on the ``SMTP`` instance.  (Closes #20)
* Fixed a new incompatibility with the ``atpublic`` library.

1.0a3 (2016-11-24)
==================
* Fix typo in ``Message.prepare_message()`` handler.  The crafted
  ``X-RcptTos`` header is renamed to ``X-RcptTo`` for backward compatibility
  with older libraries.
* Add a few hooks to make subclassing easier:

  * ``SMTP.ehlo_hook()`` is called just before the final, non-continuing 250
    response to allow subclasses to add additional ``EHLO`` sub-responses.
  * ``SMTP.rset_hook()`` is called just before the final 250 command to allow
    subclasses to provide additional ``RSET`` functionality.
  * ``Controller.make_socket()`` allows subclasses to customize the creation
    of the socket before binding.

1.0a2 (2016-11-22)
==================
* Officially support Python 3.6.
* Fix support for both IPv4 and IPv6 based on the ``--listen`` option.  Given
  by Jason Coombs.  (Closes #3)
* Correctly handle client disconnects.  Given by Konstantin vz'One Enchant.
* The SMTP class now takes an optional ``hostname`` argument.  Use this if you
  want to avoid the use of ``socket.getfqdn()``.  Given by Konstantin vz'One
  Enchant.
* Close the transport and thus the connection on SMTP ``QUIT``.  (Closes #11)
* Added an ``AsyncMessage`` handler.  Given by Konstantin vz'One Enchant.
* Add an examples/ directory.
* Flake8 clean.

1.0a1 (2015-10-19)
==================
* Initial release.
