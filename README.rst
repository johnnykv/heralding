Beeswarm |Build Status| |coverage|
=======================

.. |Build Status| image:: https://travis-ci.org/honeynet/beeswarm.png?branch=master
                       :target: https://travis-ci.org/honeynet/beeswarm
.. |coverage| image:: https://coveralls.io/repos/honeynet/beeswarm/badge.png?brance=master
                       :target: https://coveralls.io/r/honeynet/beeswarm

A honeypot project which provides easy configuration, deployment and managment of honeypots.
Beeswarm operates by deploying fake end-user systems and services. Beeswarm uses these systems to provides 
IoC (Indication of Compromise) by observing the difference between expected and actual traffic. 
An IoC could be a certificate mismatch or the unexpected reuse of credentials (honeytokens).

Beeswarm consist of three parts:


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

BeeKeeper
=========
Beekeeper is the Web UI which can help manage the Hives/Feeders.

Preparation
-----------
It is important to make sure that the Common Name specified in the following steps matches that of the
Beekeeper server.

.. code-block::

    $>openssl genrsa -des3 -out beekeeper.key 2048
    $>openssl req -new -key beekeeper.key -out beekeeper.csr
    $>openssl x509 -req -days 3650 -in beekeeper.csr -signkey beekeeper.key -out beekeeper.crt
    $>openssl rsa -in beekeeper.key -out beekeeper.key

Sample Usage
------------

.. code-block::

    $> beeswarm -be
    2013-07-14 21:12:13,571 (root) Copying configuration file to workdir.
    2013-07-14 21:12:14,917 (root) Created default admin account for the BeeKeeper.
    Default password for the admin account is: gonz
    2013-07-14 21:12:14,918 (beeswarm.beekeeper.beekeeper) Starting Beekeeper listening on port 5000
    127.0.0.1 - - [2013-07-14 21:12:33] "GET / HTTP/1.1" 302 740 0.011379
    127.0.0.1 - - [2013-07-14 21:12:33] "GET /login?next=%2F HTTP/1.1" 200 2874 0.051743
    127.0.0.1 - - [2013-07-14 21:12:33] "GET /static/css/bootstrap.min.css HTTP/1.1" 304 524 0.006433
    127.0.0.1 - - [2013-07-14 21:12:34] "GET /static/css/bootstrap-responsive.min.css HTTP/1.1" 304 523 0.002585
    127.0.0.1 - - [2013-07-14 21:12:34] "GET /static/css/font-awesome.min.css HTTP/1.1" 304 523 0.002665
    127.0.0.1 - - [2013-07-14 21:12:34] "GET /static/js/jquery-1.9.1.min.js HTTP/1.1" 304 523 0.002930
    127.0.0.1 - - [2013-07-14 21:12:34] "GET /static/js/bootstrap.min.js HTTP/1.1" 304 524 0.003524
    2013-07-14 21:12:53,688 (root) User admin logged in.
    127.0.0.1 - - [2013-07-14 21:12:53] "POST /login?next=%2F HTTP/1.1" 302 766 0.021954
    127.0.0.1 - - [2013-07-14 21:12:53] "GET / HTTP/1.1" 200 11016 0.147886
    127.0.0.1 - - [2013-07-14 21:12:54] "GET /static/css/watable.css HTTP/1.1" 200 4975 0.037256
    127.0.0.1 - - [2013-07-14 21:12:54] "GET /static/js/jquery.watable.js HTTP/1.1" 200 66523 0.075484



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


