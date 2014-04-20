# Copyright (C) 2013 Johnny Vestergaard <jkv@unixcluster.dk>
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
import uuid

from beeswarm.drones.honeypot.consumer.loggers.hpfeedslogger import HPFeedsLogger
from beeswarm.drones.honeypot.models.session import Session


class HPFeedsTests(unittest.TestCase):
    def test_hpfeeds(self):
        """
        Tests that we can connect and transmit to hpfeeds without errors.
        """
        config = {'log_hpfeedslogger': {}}
        config['log_hpfeedslogger']['host'] = 'hpfriends.honeycloud.net'
        config['log_hpfeedslogger']['port'] = 20000
        #Yes, this secret is left here intentionally...
        config['log_hpfeedslogger']['secret'] = 'XDNNuMGYUuWFaWyi'
        config['log_hpfeedslogger']['ident'] = 'HBmU08rR'
        config['log_hpfeedslogger']['chan'] = 'test.test'
        config['log_hpfeedslogger']['port_mapping'] = '{}'

        Session.authenticator = object()
        session = Session('192.168.1.1', 1234, 'test_protocol', None,
                          destination_ip='192.168.1.2', destination_port=4444)
        session.honeypot_id = uuid.uuid4()

        sut = HPFeedsLogger(config)
        sut.log(session)
        result = sut.hpc.wait(2)
        self.assertIsNone(result)
