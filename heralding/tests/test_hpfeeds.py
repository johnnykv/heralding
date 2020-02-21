# Copyright (C) 2017 Johnny Vestergaard <jkv@unixcluster.dk>
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

from heralding.reporting.hpfeeds_logger import HpFeedsLogger


class FtpTests(unittest.TestCase):

  def test_hpfeeds(self):
    """Basic test for hpfeeds reporter"""

    session_channel = "heralding.session"
    auth_channel = "heraldign.auth"
    host = "127.0.0.1"
    port = 12345
    ident = "atzqøl"
    secret = "toosecret"

    HpFeedsLogger(session_channel, auth_channel, host, port, ident, secret)
