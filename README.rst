Beeswarm |Build Status| |coverage| |landscape| 
==============================================

.. |Build Status| image:: https://travis-ci.org/honeynet/beeswarm.png?branch=master
                       :target: https://travis-ci.org/honeynet/beeswarm
.. |coverage| image:: https://coveralls.io/repos/honeynet/beeswarm/badge.png?brance=master
                       :target: https://coveralls.io/r/honeynet/beeswarm
.. |landscape| image:: https://landscape.io/github/honeynet/beeswarm/master/landscape.png
   :target: https://landscape.io/github/honeynet/beeswarm/master
   :alt: Code Health
   
Note: This project is not ready for production deployments!

Beeswarm is a honeypot project which provides easy configuration, deployment and managment of honeypots.
Beeswarm operates by deploying fake end-user systems (clients) and services (honeypots). Beeswarm uses these systems to provides
IoC (Indication of Compromise) by observing the difference between expected and actual traffic. 
An IoC could be a certificate mismatch or the unexpected reuse of credentials (honeytokens).

Installation
------------
Beeswarm is packaged as a regular python module, and follows normal installation methodology:

.. code-block:: shell

    $>python setup.py install


Developers are encouraged to use the develop feature from distribute:

.. code-block:: shell

    $>python setup.py develop


Starting the server

Starting the server
-------------------

.. code-block::

    $> mkdir server_workdir
	$> beeswarm --se
	*** Please answer a few configuration options ***
	2014-05-03 23:25:29,516 (root) Beeswarm server has been configured using default ssl parameters and network configuration, this could be used to fingerprint the beeswarm server. If you want to customize these options please use the --customize options on first startup.
	2014-05-03 23:25:29,516 (beeswarm.shared.helpers) Creating SSL Certificate and Key.

	* Communication between drones (honeypots and clients) and server *
	* Please make sure that drones can always contact the Beeswarm server using the information that you are about to enter. *
	IP or hostname of server: 192.168.1.147
	2014-05-03 23:25:46,024 (beeswarm.server.webapp.auth) Created default admin account for the beeswarm server.
	****************************************************************************
	Default password for the admin account is: wpwaitacsxhqqo
	****************************************************************************
	2014-05-03 23:25:46,027 (beeswarm.server.server) Starting server listening on port 5000
	2014-05-03 23:29:54,077 (beeswarm.server.server) Server started and priviliges dropped.


The grand scheme
================

The following deployment diagram shows the Beeswarm concept when fully operational:

.. code-block::

               +- - - - - - - - - - - - - L O G  D A T A- - - - - - - - - - - - - >>>+-----------------+
               |                                                                     | Beeswarm server |
                                                                                     +-----------------+
               |                      (bait sessions)                                      ^   ^
        +------+--------+                   Traffic                                        |   |
        |Beeswarm Client|+------------------------------------------------+                |   |
        +---------------+         ^                                       |                |   |
          (Static IP)             |                                       |       L O G    |   |
                                  |Intercept creds.                       |       D A T A      |
                                  |                                       |                |
                                  |                                       v                |   |
                          +-------+------+     Reuse credentials    +-----------------+    |   |
                          |  Evil dudes  |+------------------------>|Beeswarm Honeypot|+-+ |   |
                          +-------+------+                          +-----------------+
                                  |                                  (Static ip)               |
                                  |Operates exit node                     ^
                                  |(and intercepting creds)               |                    |
                                  |                                       |
                                  v                                       |                    |
        +---------------+    +-------------+                              |
        |Beeswarm client|+-->|TOR Exit Node|+-----------------------------+                    |
        +-----+---------+    +-------------+               Traffic
                |                                    (bait sessions)                           |

                |                                                                              |
                +- - - - - - - - - - - - - L O G  D A T A- - - - - - - - - - - - - - - - - - - -



Lead developer
--------------
Lead developer and administrator for this project is `Johnny Vestergaard <mailto:jkv@unixcluster.dk>`_.


