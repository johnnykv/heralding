==============
 Introduction
==============

This library provides an `asyncio <https://pypi.python.org/pypi/asyncio>`__
based implementation of a server for
`RFC 5321 <http://www.faqs.org/rfcs/rfc5321.html>`__ -
Simple Mail Transfer Protocol (SMTP) and
`RFC 2033 <http://www.faqs.org/rfcs/rfc2033.html>`__ -
Local Mail Transfer Protocol (LMTP).  It is derived from
`Python 3's smtpd.py <https://hg.python.org/cpython/file/3.5/Lib/smtpd.py>`__
standard library module, and provides both a command line interface and an API
for use in testing applications that send email.

Inspiration for this library comes from several other packages:

* `lazr.smtptest <http://bazaar.launchpad.net/~lazr-developers/lazr.smtptest/devel/files>`__
* `benjamin-bader/aiosmtp <https://github.com/benjamin-bader/aiosmtp>`__
* `Mailman 3's LMTP server <https://gitlab.com/mailman/mailman/blob/master/src/mailman/runners/lmtp.py#L138>`__

``aiosmtpd`` takes the best of these and consolidates them in one place.


Relevant RFCs
=============

* `RFC 5321 <http://www.faqs.org/rfcs/rfc5321.html>`__ - Simple Mail Transfer
  Protocol (SMTP)
* `RFC 2033 <http://www.faqs.org/rfcs/rfc2033.html>`__ - Local Mail Transfer
  Protocol (LMTP)
* `RFC 2034 <http://www.faqs.org/rfcs/rfc2034.html>`__ - SMTP Service
  Extension for Returning Enhanced Error Codes
* `RFC 6531 <http://www.faqs.org/rfcs/rfc6531.html>`__ - SMTP Extension for
  Internationalized Email


Other references
================

* `Wikipedia page on SMTP <https://en.wikipedia.org/wiki/Simple_Mail_Transfer_Protocol>`__
* `asyncio module documentation <https://docs.python.org/3/library/asyncio.html>`__
* `Developing with asyncio <https://docs.python.org/3/library/asyncio-dev.html#asyncio-dev>`__
* `Python issue #25508 <http://bugs.python.org/issue25008>`__ which started
  the whole thing.
