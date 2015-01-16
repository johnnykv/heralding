# Copyright (C) 2015 Johnny Vestergaard <jkv@unixcluster.dk>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import unittest
import tempfile
import shutil
import os

from beeswarm.drones.client.client import Client


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.isdir(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)

    def test_client_startup(self):
        # basic test that checks if we instantiate the Client class without errors.

        config = {'general': {'id': 1234, 'fetch_ip': True},
                  "beeswarm_server": {
                      "zmq_command_url": "tcp://127.0.0.1:5713",
                      "zmq_url": "tcp://127.0.0.1:5712",
                      "zmq_own_public": [
                          "#   ****  Generated on 2015-01-13 21:02:44.933568 by pyzmq  ****\n",
                          "#   ZeroMQ CURVE Public Certificate\n",
                          "#   Exchange securely, or use a secure mechanism to verify the contents\n",
                          "#   of this file after exchange. Store public certificates in your home\n",
                          "#   directory, in the .curve subdirectory.\n",
                          "\n",
                          "metadata\n",
                          "curve\n",
                          "    public-key = \"LeZkQ^HXijnRahQkp$&nxpu6Hh>7YHBOzbz[iJg^\"\n"
                      ],
                      "zmq_own_private": [
                          "#   ****  Generated on 2015-01-13 21:02:44.933568 by pyzmq  ****\n",
                          "#   ZeroMQ CURVE **Secret** Certificate\n",
                          "#   DO NOT PROVIDE THIS FILE TO OTHER USERS nor change its permissions.\n",
                          "\n",
                          "metadata\n",
                          "curve\n",
                          "    public-key = \"LeZkQ^HXijnRahQkp$&nxpu6Hh>7YHBOzbz[iJg^\"\n",
                          "    secret-key = \"B{(o5Hpx{[D3}>f*O{NZ(}.e3o5Xh+eO9-fmt0tb\"\n"
                      ],
                      "zmq_server_public": [
                          "#   ****  Generated on 2015-01-13 20:59:19.308358 by pyzmq  ****\n",
                          "#   ZeroMQ CURVE Public Certificate\n",
                          "#   Exchange securely, or use a secure mechanism to verify the contents\n",
                          "#   of this file after exchange. Store public certificates in your home\n",
                          "#   directory, in the .curve subdirectory.\n",
                          "\n",
                          "metadata\n",
                          "curve\n",
                          "    public-key = \"^xk>t(V(bj70]=zl.uX=)#@kYwlgjitkfrVo!I+=\"\n"
                      ]
                  }
        }

        client = Client(self.tmp_dir, config)




