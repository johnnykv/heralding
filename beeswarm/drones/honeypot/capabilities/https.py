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


import logging

from beeswarm.drones.honeypot.capabilities.http import http, BeeHTTPHandler
from beeswarm.drones.honeypot.capabilities.handlerbase import HandlerBase


logger = logging.getLogger(__name__)


class BeeHTTPSHandler(BeeHTTPHandler):
    """
        This class doesn't do anything about HTTPS, the difference is in the way the
        HTML body is sent. We need smaller chunks for HTTPS apparently.
    """

    def send_html(self, filename):
        with self.vfs.open(filename) as f:
            while True:
                chunk = f.read(1024)
                if not chunk:
                    break
                self.request.send(chunk)


class https(http, HandlerBase):
    """
    This class will get wrapped in SSL. This is possible because we by convention wrap
    all capabilities that ends with the letter 's' in SSL."""

    HandlerClass = BeeHTTPSHandler
