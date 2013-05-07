Beeswarm |Build Status|
=======================

.. |Build Status| image:: https://travis-ci.org/honeynet/beeswarm.png?branch=master
                       :target: https://travis-ci.org/honeynet/beeswarm

A honeytoken project which will try to estimate how, where and when credentials are intercepted and reused.
The project will eventually consist of three parts:


* Hive

  * Multiprotocol credentials catching honeypot, comes default with ssh, vnc, pop3, pop3s, ssh, smtp, ftp, http and telnet capability.
  * Extendable, both in terms of new protocols but can also be extended to provide shell-like features.
  * Supports a variety of loggers (syslog, file logging, hpfeeds, etc).
  * Can be deployed independently or as part of the full beeswarm setup.

* Feeder

  * Simulates a realistic environment using honeybees.

* Beekeeper

  * Provides management interface.
  * Processes data from Hive and Feeder.
  * Reports malicious activity.
  * Generates configuration and crypto keys for a full beeswarm setup.


Installation
------------
Beeswarm is packaged as a regular python module, and follows normal installation methodology:

.. code-block:: shell

    $>python setup.py install


Developers are encouraged to use the develop feature from distribute:

.. code-block:: shell

    $>python setup.py develop


Hive
====
The following sections shows how hive can be used as a standalone credentials-catching honeypot.

Preparation
-----------

.. code-block::

    $>mkdir workdir
    $>cd workdir
    $>sudo beeswarm -hi --prepare


Sample usage
------------

.. code-block::

    $>sudo python run_hive.py -v
    2013-02-21 10:36:05,975 (root) Consumer created.
    2013-02-21 10:36:05,976 (root) Started pop3 capability listening on port 110
    2013-02-21 10:36:05,976 (root) Started pop3s capability listening on port 995
    2013-02-21 10:36:05,976 (root) Started telnet capability listening on port 23
    2013-02-21 10:36:05,976 (root) Started ssh capability listening on port 2222
    2013-02-21 10:36:05,976 (root) Started ftp capability listening on port 21
    2013-02-21 10:36:05,976 (root) Started vnc capability listening on port 5900
    2013-02-21 10:36:05,980 (root) Privileges dropped, running as nobody/nobody.
    2013-02-21 10:36:05,982 (hive.consumer.loggers.hpfeeds) Connecting to feed broker at hpfeeds.honeycloud.net:10000
    2013-02-21 10:36:06,012 (hive.consumer.loggers.hpfeeds) Connected to hpfeed broker.
    2013-02-21 10:37:01,444 (hive.models.session) telnet authentication attempt from 192.168.1.123. [james/bond] (7cee7b1c-2b1b-42ac-a963-156ecb58f2f1)
    2013-02-21 10:37:49,787 (hive.models.session) ssh authentication attempt from 192.168.1.123. [root/toor] (6cda8971-aefd-41a6-9a96-caf4c7407028)
    2013-02-21 10:37:50,113 (hive.models.session) ssh authentication attempt from 192.168.1.123. [root/qwerty] (6cda8971-aefd-41a6-9a96-caf4c7407028)


The grand scheme
================

The following deployment diagram shows the Beeswarm concept when fully operational:

.. code-block::

               +- - - - - - - - - - - - - L O G  D A T A- - - - - - - - - - - - - >>>+------------+
               |                                                                     | Beekeeper |
                                                                                     +------------+
               |                        (honeybees)                                        ^   ^
          +----+------+                   Traffic                                              |
          |   Feeder  |+--------------------------------------------------+                |
          +-----------+           ^                                       |                    |
          (Static IP)             |                                       |         L O G  |
                                  |Intercept creds.                       |         D A T A    |
                                  |                                       |                |
                                  |                                       v                    |
                          +-------+------+     Reuse credentials    +------------+         |
                          |  Evil dudes  |+------------------------>|    Hive    |+ - - - -+   |
                          +-------+------+                          +------------+
                                  |                                  (Static ip)               |
                                  |Operates exit node                     ^
                                  |(and intercepting creds)               |                    |
                                  |                                       |
                                  v                                       |                    |
          +-----------+    +-------------+                                |
          |   Feeder  |+-->|TOR Exit Node|+-------------------------------+                    |
          +-----+-----+    +-------------+               Traffic
                |                                      (honeybees)                             |

                |                                                                              |
                +- - - - - - - - - - - - - L O G  D A T A- - - - - - - - - - - - - - - - - - - -


Data access
-----------

The Hive part of the system is operational and are currently collecting data. Members of the `The Honeynet Project <http://www.honeynet.org/>`_ 
can gain access to this data by subscribing to the *beeswarm.hive* hpfeeds channel, or preferably access the data through the `Mnemosyne <https://github.com/johnnykv/mnemosyne>`_ `REST api <http://johnnykv.github.com/mnemosyne/WebAPI.html#resources-as-of-version-1>`_.

Lead developer
--------------
Lead developer and administrator for this project is `Johnny Vestergaard <mailto:jkv@unixcluster.dk>`_.


