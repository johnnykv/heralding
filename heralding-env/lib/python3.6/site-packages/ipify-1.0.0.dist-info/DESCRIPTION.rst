python-ipify
============

The official client library for `ipify <http://www.ipify.org/>`_: *A Simple IP
Address API*.

.. image:: https://img.shields.io/pypi/v/ipify.svg
    :alt: python-ipify Release
    :target: https://pypi.python.org/pypi/ipify

.. image:: https://img.shields.io/pypi/dm/ipify.svg
    :alt: python-ipify Downloads
    :target: https://pypi.python.org/pypi/ipify

.. image:: https://img.shields.io/travis/rdegges/python-ipify.svg
    :alt: python-ipify Build
    :target: https://travis-ci.org/rdegges/python-ipify

.. image:: https://coveralls.io/repos/rdegges/python-ipify/badge.svg?branch=master
    :target: https://coveralls.io/r/rdegges/python-ipify?branch=master


Meta
----

- Author: Randall Degges
- Email: r@rdegges.com
- Site: http://www.rdegges.com
- Status: maintained, active


Purpose
-------

`ipify <http://www.ipify.org/>`_ is the best IP address lookup service on the
internet.  It's fast, simple, scalable, open source, and well-funded (*by me!*).

In short: if you need a way to pragmatically get your public IP address, ipify
is the best possible choice!

This library will retrieve your public IP address from ipify's API service, and
return it as a string.  It can't get any simpler than that.

This library also has some other nice features you might care about:

- If a request fails for any reason, it is re-attempted 3 times using an
  exponential backoff algorithm for maximum effectiveness.
- This library handles exceptions properly, and usage examples below show you
  how to deal with errors in a foolproof way.
- This library only makes API requests over HTTPS.


Installation
------------

To install ``ipify``, simply run:

.. code-block:: console

    $ pip install ipify

This will install the latest version of the library automatically.


Usage
-----

Using this library is very simple.  Here's a simple example:

.. code-block:: python

    >>> from ipify import get_ip
    >>> ip = get_ip()
    >>> ip
    u'96.41.136.144'

Now, in regards to exception handling, there are several ways this can fail:

- The ipify service is down (*not likely*), or:
- Your machine is unable to get the request to ipify because of a network error
  of some sort (DNS, no internet, etc.).

Here's how you can handle all of these edge cases:

.. code-block:: python

    from ipify import get_ip
    from ipify.exceptions import ConnectionError, ServiceError

    try:
        ip = get_ip()
    except ConnectionError:
        # If you get here, it means you were unable to reach the ipify service,
        # most likely because of a network error on your end.
    except ServiceError:
        # If you get here, it means ipify is having issues, so the request
        # couldn't be completed :(
    except:
        # Something else happened (non-ipify related). Maybe you hit CTRL-C
        # while the program was running, the kernel is killing your process, or
        # something else all together.

If you want to simplify the above error handling, you could also do the
following (*it will catch any sort of ipify related errors regardless of what
type they may be*):

.. code-block:: python

    from ipify import get_ip
    from ipify.exceptions import IpifyException

    try:
        ip = get_ip()
    except IpifyException:
        # If you get here, then some ipify exception occurred.
    except:
        # If you get here, some non-ipify related exception occurred.

One thing to keep in mind: regardless of how you decide to handle exceptions,
the ipify library will retry any failed requests 3 times before ever raising
exceptions -- so if you *do* need to handle exceptions, just remember that retry
logic has already been attempted.


Contributing
------------

This project is only possible due to the amazing contributors who work on it!

If you'd like to improve this library, please send me a pull request! I'm happy
to review and merge pull requests.

The standard contribution workflow should look something like this:

- Fork this project on Github.
- Make some changes in the master branch (*this project is simple, so no need to
  complicate things*).
- Send a pull request when ready.

Also, if you're making changes, please write tests for your changes -- this
project has a full test suite you can easily modify / test.

To run the test suite, you can use the following commands:

.. code-block:: console

    $ pip install -e .
    $ pip install -r requirements.txt
    $ python manage.py test


Change Log
----------

All library changes, in descending order.


Version 1.0.0
*************

**Released May 6, 2015.**

- First release!


