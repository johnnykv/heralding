==========
 Concepts
==========

There are two general ways you can run the SMTP server, via the :ref:`command
line <cli>` or :ref:`programmatically <controller>`.

There are several dimensions in which you can extend the basic functionality
of the SMTP server.  You can implement an *event handler* which uses well
defined :ref:`handler hooks <hooks>` that are called during the various steps
in the SMTP dialog.  If such a hook is implemented, it assumes responsibility
for the status messages returned to the client.

You can also :ref:`subclass <subclass>` the core ``SMTP`` class to implement
new commands, or change the semantics of existing commands.

For example, if you wanted to print the received message on the console, you
could implement a handler that hooks into the ``DATA`` command.  The contents
of the message will be available on one of the hook's arguments, and your
handler could print this content to stdout.

On the other hand, if you wanted to implement an SMTP-like server that adds a
new command called ``PING``, you would do this by subclassing ``SMTP``, adding
a method that implements whatever semantics for ``PING`` that you want.


.. _sessions_and_envelopes:

Sessions and envelopes
======================

Two classes are used during the SMTP dialog with clients.  Instances of these
are passed to the handler hooks.


Session
-------

The session represents the state built up during a client's socket connection
to the server.  Each time a client connects to the server, a new session
object is created.

.. class:: Session()

   .. attribute:: peer

      Defaulting to None, this attribute will contain the transport's socket's
      peername_ value.

   .. attribute:: ssl

      Defaulting to None, this attribute will contain some extra information,
      as a dictionary, from the ``asyncio.sslproto.SSLProtocol`` instance.
      This dictionary provides additional information about the connection.
      It contains implementation-specific information so its contents may
      change, but it should roughly correspond to the information available
      through `this method`_.

   .. attribute:: host_name

      Defaulting to None, this attribute will contain the host name argument
      as seen in the ``HELO`` or ``EHLO`` (or for :ref:`LMTP <LMTP>`, the
      ``LHLO``) command.

   .. attribute:: extended_smtp

      Defaulting to False, this flag will be True when the ``EHLO`` greeting
      was seen, indicating ESMTP_.

   .. attribute:: loop

      This is the asyncio event loop instance.


Envelope
--------

The envelope represents state built up during the client's SMTP dialog.  Each
time the protocol state is reset, a new envelope is created.  E.g. when the
SMTP ``RSET`` command is sent, the state is reset and a new envelope is
created.  A new envelope is also created after the ``DATA`` command is
completed, or in certain error conditions as mandated by `RFC 5321`_.

.. class:: Envelope

   .. attribute:: mail_from

      Defaulting to None, this attribute holds the email address given in the
      ``MAIL FROM`` command.

   .. attribute:: mail_options

      Defaulting to None, this attribute contains a list of any ESMTP mail
      options provided by the client, such as those passed in by `the smtplib
      client`_.

   .. attribute:: content

      Defaulting to None, this attribute will contain the contents of the
      message as provided by the ``DATA`` command.  If the ``decode_data``
      parameter to the ``SMTP`` constructor was True, then this attribute will
      contain the UTF-8 decoded string, otherwise it will contain the raw
      bytes.

   .. attribute:: original_content

      Defaulting to None, this attribute will contain the contents of the
      message as provided by the ``DATA`` command.  Unlike the ``content``
      attribute, this attribute will always contain the raw bytes.

   .. attribute:: rcpt_tos

      Defaulting to the empty list, this attribute will contain a list of the
      email addresses provided in the ``RCPT TO`` commands.

   .. attribute:: rcpt_options

      Defaulting to the empty list, this attribute will contain the list of
      any recipient options provided by the client, such as those passed in by
      `the smtplib client`_.


.. _peername: https://docs.python.org/3/library/asyncio-protocol.html?highlight=peername#asyncio.BaseTransport.get_extra_info
.. _`this method`: https://docs.python.org/3/library/asyncio-protocol.html?highlight=get_extra_info#asyncio.BaseTransport.get_extra_info
.. _ESMTP: http://www.faqs.org/rfcs/rfc1869.html
.. _`the smtplib client`: https://docs.python.org/3/library/smtplib.html#smtplib.SMTP.sendmail
.. _`RFC 5321`: http://www.faqs.org/rfcs/rfc5321.html
