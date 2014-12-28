# Copyright (C) 2013 Aniket Panse <contact@aniketpanse.in>
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

# Aniket Panse <contact@aniketpanse.in> grants Johnny Vestergaard <jkv@unixcluster.dk>
# a perpetual, worldwide, non-exclusive, no-charge, royalty-free, irrevocable
# copyright license to reproduce, prepare derivative works of, publicly
# display, publicly perform, sublicense, relicense, and distribute [the] Contributions
# and such derivative works.


import gevent.monkey

gevent.monkey.patch_all()

import unittest
import os
import shutil
import tempfile

from gevent.server import StreamServer
from beeswarm.drones.honeypot.honeypot import Honeypot
from beeswarm.drones.honeypot.capabilities import smtp as honeypot_smtp

from beeswarm.drones.client.baits import smtp as bee_smtp
from beeswarm.drones.client.models.session import BaitSession


class SmtpTest(unittest.TestCase):
    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        Honeypot.prepare_environment(self.work_dir)

    def tearDown(self):
        if os.path.isdir(self.work_dir):
            shutil.rmtree(self.work_dir)

    def test_login(self):
        """Tests if the SMTP bait can login to the SMTP capability"""

        options = {'enabled': 'True', 'port': 0, 'protocol_specific_data': {'banner': 'Test'},
                   'users': {'test': 'test'}}
        cap = honeypot_smtp.smtp(options, self.work_dir)
        srv = StreamServer(('0.0.0.0', 0), cap.handle_session)
        srv.start()

        bee_info = {
            'timing': 'regular',
            'username': 'test',
            'password': 'test',
            'port': srv.server_port,
            'server': '127.0.0.1',
            'local_hostname': 'testhost',
            'honeypot_id': '1234'
        }
        beesessions = {}

        BaitSession.client_id = 'f51171df-c8f6-4af4-86c0-f4e163cf69e8'
        current_bait = bee_smtp.Smtp(bee_info)
        current_bait.connect()
        current_bait.login(bee_info['username'], bee_info['password'])
        srv.stop()

    def test_login(self):
        """Tests if the SMTP bait can send emails to the SMTP capability"""

        options = {'enabled': 'True', 'port': 0, 'protocol_specific_data': {'banner': 'Test'},
                   'users': {'test': 'test'}}

        cap = honeypot_smtp.smtp(options, self.work_dir)
        srv = StreamServer(('0.0.0.0', 0), cap.handle_session)
        srv.start()

        bee_info = {
            'timing': 'regular',
            'username': 'test',
            'password': 'test',
            'port': srv.server_port,
            'server': '127.0.0.1',
            'local_hostname': 'testhost'
        }
        beesessions = {}

        BaitSession.client_id = 'f51171df-c8f6-4af4-86c0-f4e163cf69e8'
        current_bee = bee_smtp.Smtp(bee_info)
        current_bee.connect()
        current_bee.login(bee_info['username'], bee_info['password'])
        result = current_bee.client.sendmail('sender@test.com', 'reciever@test.com', 'Just testing the SMTP bait')
        self.assertEquals(result, {})
        srv.stop()

    def test_retrieve(self):
        """ Tests if a mail can be properly retrieved from the mail corpus """

        options = {'enabled': 'True', 'port': 0, 'protocol_specific_data': {'banner': 'Test'},
                   'users': {'test': 'test'}}

        cap = honeypot_smtp.smtp(options, self.work_dir)
        srv = StreamServer(('0.0.0.0', 0), cap.handle_session)
        srv.start()
        gevent.sleep()
        bait_info = {
            'timing': 'regular',
            'username': 'test',
            'password': 'test',
            'port': srv.server_port,
            'server': '127.0.0.1',
            'local_hostname': 'testhost'
        }

        BaitSession.client_id = 'f51171df-c8f6-4af4-86c0-f4e163cf69e8'
        current_bee = bee_smtp.Smtp(bait_info)

        from_addr, to_addr, mail_body = current_bee.get_one_mail()
        self.assertGreater(len(from_addr), 0)
        self.assertGreater(len(to_addr), 0)
        self.assertGreater(len(mail_body), 0)


if __name__ == '__main__':
    unittest.main()
