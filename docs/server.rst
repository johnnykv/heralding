Beeswarm Server
===============

The central beeswarm server is a web-app built on the `Flask <http://flask.pocoo.org/>`_
framework. It makes the creation and deployment of Hives and Feeders
easy. It is the management interface for Beeswarm and, does the data
processing too. It makes deployment easy by generating bootable ISO
files for Honeypot/Client. In order for it to be able to do this, it uses
a base ISO file, which is modified as per the configuration.

Generating a Base ISO file
----------------------------

In order to enable support for bootable ISO creation, there needs to
be a base ISO file in the working directory of Beeswarm. This section
details the steps necessary to create the Base ISO.

1. Installing Debian Live
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Beeswarm uses Debian Live to generate Base ISO files. Since all versions
of Debian Live are not fully compatible with each other, it is recommended
that ``live-build`` version 3.0.5-1 be used. It can be downloaded from `Debian Packages
<http://packages.debian.org/wheezy/live-build>`_. It depends on the
``debootstrap`` package, which can be found `here <http://packages.debian.org/wheezy/debootstrap>`_.
Note that the Debian packages can be used regardless of the host Linux Distribution.
So installing the above packages on say, Ubuntu, is totally fine.

.. code-block:: shell

    # dpkg -i debootstrap_*.deb live-build_*.deb

2. Creating the ISO
~~~~~~~~~~~~~~~~~~~~~

In order to create the ISO, one must first clone the Beeswarm GitHub repository.

.. code-block:: shell

    $ git clone https://github.com/honeynet/beeswarm.git

Then enter the ``tools/live-build`` directory and execute the build_iso.sh script:

.. code-block:: shell

    $ cd tools/live-build
    $ sudo sh build_iso.sh

Afterwards you can find the generated ISO as beeswarm_client.iso:

.. code-block:: shell

    $ ls -la beeswarm_client.iso
    -rw-r--r-- 1 root root 305135616 Oct  4 19:04 beeswarm_client.iso
