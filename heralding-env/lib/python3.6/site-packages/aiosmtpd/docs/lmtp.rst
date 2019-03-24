.. _LMTP:

================
 The LMTP class
================

`RFC 2033 <http://www.faqs.org/rfcs/rfc2033.html>`_ defines the Local Mail
Transport Protocol.  In many ways, this is very similar to SMTP, but with no
guarantees of queuing.  It is, in a sense, an alternative to ESMTP, and is
often used for local mail routing (e.g. from a Mail Transport Agent to a local
command or system) where the unreliability of internet connectivity is not an
issue.

The ``LMTP`` class subclasses the ``SMTP`` class and its only functional
difference is that it implements the ``LHLO`` command, and prohibits the use
of ``HELO`` and ``EHLO``.
