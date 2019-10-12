Heralding |travis badge| |version badge| |codacy badge|
=======================================================

.. |travis badge| image:: https://img.shields.io/travis/johnnykv/heralding/master.svg
   :target: https://travis-ci.org/johnnykv/heralding
.. |codacy badge| image:: https://api.codacy.com/project/badge/Grade/e9419eb118dc4741ae230aa6bcc8a015
   :target: https://www.codacy.com/app/johnnykv/heralding?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=johnnykv/heralding&amp;utm_campaign=Badge_Grade
.. |version badge| image:: https://img.shields.io/pypi/v/heralding.svg
   :target: https://pypi.python.org/pypi/Heralding/
   
   
About
-----

Sometimes you just want a simple honeypot that collects credentials, nothing more. Heralding is that honeypot!
Currently the following protocols are supported: ftp, telnet, ssh, http, https, pop3, pop3s, imap, imaps, smtp, vnc, postgresql and socks5.

**You need Python 3.5.0 or higher.**

Starting the honeypot
-----------------------

.. code-block:: shell

   2019-04-14 13:10:11,854 (root) Initializing Heralding version 1.0.4
   2019-04-14 13:10:11,879 (heralding.reporting.file_logger) File logger: Using log_auth.csv to log authentication attempts in CSV format.
   2019-04-14 13:10:11,879 (heralding.reporting.file_logger) File logger: Using log_session.csv to log unified session data in CSV format.
   2019-04-14 13:10:11,879 (heralding.reporting.file_logger) File logger: Using log_session.json to log complete session data in JSON format.
   2019-04-14 13:10:11,880 (heralding.honeypot) Started Pop3 capability listening on port 110
   2019-04-14 13:10:11,882 (heralding.honeypot) Started Pop3S capability listening on port 995
   2019-04-14 13:10:11,883 (heralding.honeypot) Started smtp capability listening on port 25
   2019-04-14 13:10:11,883 (heralding.honeypot) Started Http capability listening on port 80
   2019-04-14 13:10:11,885 (heralding.honeypot) Started https capability listening on port 443
   2019-04-14 13:10:11,885 (heralding.honeypot) Started Vnc capability listening on port 5900
   2019-04-14 13:10:11,885 (heralding.honeypot) Started Telnet capability listening on port 23
   2019-04-14 13:10:11,886 (heralding.honeypot) Started ftp capability listening on port 21
   2019-04-14 13:10:11,886 (heralding.honeypot) Started Imap capability listening on port 143
   2019-04-14 13:10:11,886 (heralding.honeypot) Started MySQL capability listening on port 3306
   2019-04-14 13:10:11,887 (heralding.honeypot) Started Socks5 capability listening on port 1080
   2019-04-14 13:10:11,946 (asyncssh) Creating SSH server on 0.0.0.0, port 2222
   2019-04-14 13:10:11,946 (heralding.honeypot) Started SSH capability listening on port 2222
   2019-04-14 13:10:11,946 (heralding.honeypot) Started PostgreSQL capability listening on port 5432
   2019-04-14 13:10:11,947 (heralding.honeypot) Started Imaps capability listening on port 993


Viewing the collected data
--------------------------

Heralding logs relevant data in three files, log_session.json, log_auth.csv and log_session.json.

**log_session.json**

This log file contains all available information for a given activity to the honeypot. This included timestamp, authentication attempts and protocol specific information (auxiliary data) - and a bunch of other information. Be aware that the log entry for a specific session will appear in the log fil **after** the session has ended. The format is jsonlines.

.. code-block:: json

   {  
     "timestamp":"2019-04-13 08:29:09.019394",
     "duration":9,
     "session_id":"4ba1fc0a-872c-46bb-a2f8-80c38453c74f",
     "source_ip":"127.0.0.1",
     "source_port":52192,
     "destination_ip":"127.0.0.1",
     "destination_port":2222,
     "protocol":"ssh",
     "num_auth_attempts":2,
     "auth_attempts":[  
       {  
         "timestamp":"2019-04-13 08:29:12.732530",
         "username":"rewt",
         "password":"PASSWORD"
       },
       {  
         "timestamp":"2019-04-13 08:29:15.686619",
         "username":"rewt",
         "password":"P@ssw0rd12345"
       },
     ],
     "session_ended":true,
     "auxiliary_data":{  
       "client_version":"SSH-2.0-OpenSSH_7.7p1 Ubuntu-4ubuntu0.3",
       "recv_cipher":"aes128-ctr",
       "recv_mac":"umac-64-etm@openssh.com",
       "recv_compression":"none"
     }
   }


**log_session.csv**

This log file contains entries for all connections to the honeypot. The data includes timestamp, duration, IP information and the number of authentication attempts. Be aware that the log entry for a specific session will appear in the log fil **after** the session has ended. 

.. code-block:: shell

 $ tail log_session.csv
 timestamp,duration,session_id,source_ip,source_port,destination_ip,destination_port,protocol,auth_attempts
 2017-12-26 20:38:19.683713,16,0841e3aa-241b-4da0-b85e-e5a5524cc836,127.0.0.1,53161,,23,telnet,3
 2017-12-26 22:17:33.140742,6,d20c30c1-6765-4ab5-9144-a8be02385018,127.0.0.1,55149,,21,ftp,1
 2017-12-26 22:17:48.088281,0,e0f50505-af93-4234-b82c-5477d8d88546,127.0.0.1,55151,,22,ssh,0
 2017-12-26 22:18:06.284689,0,6c7d653f-d02d-4717-9973-d9b2e4a41d24,127.0.0.1,55153,,22,ssh,0
 2017-12-26 22:18:13.043327,30,f3af2c8c-b63f-4873-ac7f-28c73b9e3e92,127.0.0.1,55155,,22,ssh,3

**log_auth.csv**

This log file contains information for all authentication attempts where it was possible to log a username and plaintext password. Log entries will appear in this file as soon as the password has been transmitted.

.. code-block:: shell

  $ tail log_auth.csv
  timestamp,auth_id,session_id,source_ip,source_port,destination_port,protocol,username,password
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

For step by step instructions on how to install and run heralding in a Python virtual environment using Ubuntu, see this `guide <https://github.com/johnnykv/heralding/blob/master/INSTALL.md>`_. Otherwise, the basic installation instructions are below.

To install the latest stable (well, semi-stable) version, use pip:

.. code-block:: shell

  pip install heralding

Make sure that requirements and pip is installed.
Simple way to do this on a Debian-based OS is:

.. code-block:: shell

  sudo apt-get install python-pip python-dev build-essential libssl-dev libffi-dev
  sudo pip install -r requirements.txt
  
And finally start the honeypot:
  
.. code-block:: shell

  mkdir tmp
  cd tmp
  sudo heralding
  
Pcaps
-----

Want a seperate pcap for each heralding session? Sure, take a look at the Curisoum_ project. Make sure to enable Curisoum in Heralding.yml!

.. _Curisoum: https://github.com/johnnykv/curiosum
