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

import unittest

from beeswarm.shared.vnc.decoder import VNCDecoder


class VncDecoderTests(unittest.TestCase):
    def test_combinations(self):
        """Tests different combinations of challenge/response pairs and checks if
           we can find the right password.
        """
        passwords = ['1q2w3e4r', 'asdf', '1234', 'beeswarm', 'random']


        # Real password is 1234
        challenge = '\x1f\x9c+\t\x14\x03\xfaj\xde\x97p\xe9e\xca\x08\xff'
        response = '\xe7\xe2\xe2\xa8\x89T\x87\x8d\xf01\x96\x10\xfe\xb9\xc5\xbb'

        decoder = VNCDecoder(challenge, response, passwords)
        computed_pass = decoder.decode()

        # Computed passwords are either truncated to 8 bytes, or padded with '\x00'
        # to the right, so we only check if it starts with the real password.
        self.assertEquals(computed_pass.startswith('1234'), True)


if __name__ == '__main__':
    unittest.main()
