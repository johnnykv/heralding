Heralding |travis badge| |landscape badge| |version badge|
=======================

.. |travis badge| image:: https://img.shields.io/travis/johnnykv/heralding/master.svg
   :target: https://travis-ci.org/johnnykv/heralding
.. |landscape badge| image:: https://landscape.io/github/johnnykv/heralding/master/landscape.png
   :target: https://landscape.io/johnnykv/heralding/master
   :alt: Code Health
.. |version badge| image:: https://img.shields.io/pypi/v/heralding.svg
   :target: https://pypi.python.org/pypi/Heralding/

About
-----

Sometimes you just want a simple honeypot that collects credentials, nothing more. Heralding is that honeypot!
Currently the following protocols are supported: ftp, telnet, ssh, http, https, pop3, pop3s and smtp.

Starting the honeypot
-----------------------

.. code-block:: shell

  $ sudo heralding 
  2016-03-18 20:36:47,090 (root) Initializing Heralding version 0.1.0
  2016-03-18 20:36:47,090 (root) Using default config file: "/Users/jkv/repos/heralding/heralding/heralding.yml", if you want to customize values please copy this file to the current working directory
  2016-03-18 20:36:47,098 (heralding.reporting.file_logger) File logger started, using file: heralding_activity.log
  2016-03-18 20:36:47,099 (heralding.honeypot) Started ftp capability listening on port 21
  2016-03-18 20:36:47,100 (heralding.honeypot) Started Http capability listening on port 80
  2016-03-18 20:36:47,100 (heralding.honeypot) Started Pop3 capability listening on port 110
  2016-03-18 20:36:47,100 (heralding.honeypot) Started smtp capability listening on port 25
  2016-03-18 20:36:47,268 (heralding.honeypot) Started SSH capability listening on port 22
  2016-03-18 20:36:47,268 (heralding.honeypot) Started Telnet capability listening on port 23
  2016-03-18 20:36:47,270 (root) Privileges dropped, running as nobody/nogroup.

Viewing the collected data
--------------------------

.. code-block:: shell

  $ tail -f heralding_activity.log
  timestamp,auth_id,auth_type,session_id,source_ip,source_port,destination_port,protocol,username,password
  2016-03-12 20:35:02.258198,192.168.2.129,51551,23,telnet,bond,james
  2016-03-12 20:35:09.658593,192.168.2.129,51551,23,telnet,clark,P@SSw0rd123
  2016-03-18 19:31:38.064700,192.168.2.129,53416,22,ssh,NOP_Manden,M@MS3
  2016-03-18 19:31:38.521047,192.168.2.129,53416,22,ssh,guest,guest
  2016-03-18 19:31:39.376768,192.168.2.129,53416,22,ssh,HundeMad,katNIPkat
  2016-03-18 19:33:07.064504,192.168.2.129,53431,110,pop3,charles,N00P1SH
  2016-03-18 19:33:12.504483,192.168.2.129,53431,110,pop3,NektarManden,mANDENnEktar
  2016-03-18 19:33:24.952645,192.168.2.129,53433,21,ftp,Jamie,brainfreeze
  2016-03-18 19:33:47.008562,192.168.2.129,53436,21,ftp,NektarKongen,SuperS@cretP4ssw0rd1
  2016-03-18 19:36:56.077840,192.168.2.129,53445,21,ftp,Joooop,Pooop


Installing Heralding
---------------------

To install the latest stable (well, semi-stable) version, use pip:

.. code-block:: shell

  pip install heralding
