.. _controller:

====================
 Programmatic usage
====================

If you already have an `asyncio event loop`_, you can `create a server`_ using
the ``SMTP`` class as the *protocol factory*, and then run the loop forever.
If you need to pass arguments to the ``SMTP`` constructor, use
`functools.partial()`_ or write your own wrapper function.  You might also
want to add a signal handler so that the loop can be stopped, say when you hit
control-C.

It's probably easier to use a *controller* which runs the SMTP server in a
separate thread with a dedicated event loop.  The controller provides useful
and reliable *start* and *stop* semantics so that the foreground thread
doesn't block.  Among other use cases, this makes it convenient to spin up an
SMTP server for unit tests.

In both cases, you need to pass a :ref:`handler <handlers>` to the ``SMTP``
constructor.  Handlers respond to events that you care about during the SMTP
dialog.


Using the controller
====================

Say you want to receive email for ``example.com`` and print incoming mail data
to the console.  Start by implementing a handler as follows::

    >>> import asyncio
    >>> class ExampleHandler:
    ...     async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
    ...         if not address.endswith('@example.com'):
    ...             return '550 not relaying to that domain'
    ...         envelope.rcpt_tos.append(address)
    ...         return '250 OK'
    ...
    ...     async def handle_DATA(self, server, session, envelope):
    ...         print('Message from %s' % envelope.mail_from)
    ...         print('Message for %s' % envelope.rcpt_tos)
    ...         print('Message data:\n')
    ...         print(envelope.content.decode('utf8', errors='replace'))
    ...         print('End of message')
    ...         return '250 Message accepted for delivery'

Pass an instance of your ``ExampleHandler`` class to the ``Controller``, and
then start it::

    >>> from aiosmtpd.controller import Controller
    >>> controller = Controller(ExampleHandler())
    >>> controller.start()

The SMTP thread might run into errors during its setup phase; to catch this
the main thread will timeout when waiting for the SMTP server to become ready.
By default the timeout is set to 1 second but can be changed either by using
the ``AIOSMTPD_CONTROLLER_TIMEOUT`` environment variable or by passing a
different ``ready_timeout`` duration to the Controller's constructor.

Connect to the server and send a message, which then gets printed by
``ExampleHandler``::

    >>> from smtplib import SMTP as Client
    >>> client = Client(controller.hostname, controller.port)
    >>> r = client.sendmail('a@example.com', ['b@example.com'], """\
    ... From: Anne Person <anne@example.com>
    ... To: Bart Person <bart@example.com>
    ... Subject: A test
    ... Message-ID: <ant>
    ...
    ... Hi Bart, this is Anne.
    ... """)
    Message from a@example.com
    Message for ['b@example.com']
    Message data:
    <BLANKLINE>
    From: Anne Person <anne@example.com>
    To: Bart Person <bart@example.com>
    Subject: A test
    Message-ID: <ant>
    <BLANKLINE>
    Hi Bart, this is Anne.
    <BLANKLINE>
    End of message

You'll notice that at the end of the ``DATA`` command, your handler's
``handle_DATA()`` method was called.  The sender, recipients, and message
contents were taken from the envelope, and printed at the console.  The
handler methods also returns a successful status message.

The ``ExampleHandler`` class also implements a ``handle_RCPT()`` method.  This
gets called after the ``RCPT TO`` command is sanity checked.  The method
ensures that all recipients are local to the ``@example.com`` domain,
returning an error status if not.  It is the handler's responsibility to add
valid recipients to the ``rcpt_tos`` attribute of the envelope and to return a
successful status.

Thus, if we try to send a message to a recipient not inside ``example.com``,
it is rejected::

    >>> client.sendmail('aperson@example.com', ['cperson@example.net'], """\
    ... From: Anne Person <anne@example.com>
    ... To: Chris Person <chris@example.net>
    ... Subject: Another test
    ... Message-ID: <another>
    ...
    ... Hi Chris, this is Anne.
    ... """)
    Traceback (most recent call last):
    ...
    smtplib.SMTPRecipientsRefused: {'cperson@example.net': (550, b'not relaying to that domain')}

When you're done with the SMTP server, stop it via the controller.

    >>> controller.stop()

The server is guaranteed to be stopped.

    >>> client.connect(controller.hostname, controller.port)
    Traceback (most recent call last):
    ...
    ConnectionRefusedError: ...

There are a number of built-in :ref:`handler classes <handlers>` that you can
use to do some common tasks, and it's easy to write your own handler.  For a
full overview of the methods that handler classes may implement, see the
section on :ref:`handler hooks <hooks>`.


Enabling SMTPUTF8
=================

It's very common to want to enable the ``SMTPUTF8`` ESMTP option, therefore
this is the default for the ``Controller`` constructor.  For backward
compatibility reasons, this is *not* the default for the ``SMTP`` class
though.  If you want to disable this in the ``Controller``, you can pass this
argument into the constructor::

    >>> from aiosmtpd.handlers import Sink
    >>> controller = Controller(Sink(), enable_SMTPUTF8=False)
    >>> controller.start()

    >>> client = Client(controller.hostname, controller.port)
    >>> code, message = client.ehlo('me')
    >>> code
    250

The EHLO response does not include the ``SMTPUTF8`` ESMTP option.

    >>> lines = message.decode('utf-8').splitlines()
    >>> # Don't print the server host name line, since that's variable.
    >>> for line in lines[1:]:
    ...     print(line)
    SIZE 33554432
    8BITMIME
    HELP

    >>> controller.stop()


Controller API
==============

.. class:: Controller(handler, loop=None, hostname=None, port=8025, *, ready_timeout=1.0, enable_SMTPUTF8=True, ssl_context=None)

   *handler* is an instance of a :ref:`handler <handlers>` class.

   *loop* is the asyncio event loop to use.  If not given,
   :meth:`asyncio.new_event_loop()` is called to create the event loop.

   *hostname* is passed to your loop's
   :meth:`AbstractEventLoop.create_server` method as the
   ``host`` parameter,
   except None (default) is translated to '::1'. To bind
   dual-stack locally, use 'localhost'. To bind `dual-stack
   <https://en.wikipedia.org/wiki/IPv6#Dual-stack_IP_implementation>`_
   on all interfaces, use ''.

   *port* is passed directly to your loop's
   :meth:`AbstractEventLoop.create_server` method.

   *ready_timeout* is float number of seconds that the controller will wait in
   :meth:`Controller.start` for the subthread to start its server.  You can
   also set the :envvar:`AIOSMTPD_CONTROLLER_TIMEOUT` environment variable to
   a float number of seconds, which takes precedence over the *ready_timeout*
   argument value.

   *enable_SMTPUTF8* is a flag which is passed directly to the same named
   argument to the ``SMTP`` constructor.  When True, the ESMTP ``SMTPUTF8``
   option is returned to the client in response to ``EHLO``, and UTF-8 content
   is accepted.

   *ssl_context* is an ``SSLContext`` that will be used by the loop's
   server. It is passed directly to the :meth:`AbstractEventLoop.create_server`
   method. Note that this implies unconditional encryption of the connection,
   and prevents use of the ``STARTTLS`` mechanism.

   .. attribute:: handler

      The instance of the event *handler* passed to the constructor.

   .. attribute:: loop

      The event loop being used.  This will either be the given *loop*
      argument, or the new event loop that was created.

   .. attribute:: hostname
                  port

      The values of the *hostname* and *port* arguments.

   .. attribute:: ready_timeout

      The timeout value used to wait for the server to start.  This will
      either be the float value converted from the
      :envvar:`AIOSMTPD_CONTROLLER_TIMEOUT` environment variable, or the
      *ready_timeout* argument.

   .. attribute:: server

      This is the server instance returned by
      :meth:`AbstractEventLoop.create_server` after the server has started.

   .. method:: start()

      Start the server in the subthread.  The subthread is always a daemon
      thread (i.e. we always set ``thread.daemon=True``.  Exceptions can be
      raised if the server does not start within the *ready_timeout*, or if
      any other exception occurs in while creating the server.

   .. method:: stop()

      Stop the server and the event loop, and cancel all tasks.

   .. method:: factory()

      You can override this method to create custom instances of the ``SMTP``
      class being controlled.  By default, this creates an ``SMTP`` instance,
      passing in your handler and setting the ``enable_SMTPUTF8`` flag.
      Examples of why you would want to override this method include creating
      an ``LMTP`` server instance instead, or passing in a different set of
      arguments to the ``SMTP`` constructor.


.. _`asyncio event loop`: https://docs.python.org/3/library/asyncio-eventloop.html
.. _`create a server`: https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.AbstractEventLoop.create_server
.. _`functools.partial()`: https://docs.python.org/3/library/functools.html#functools.partial
