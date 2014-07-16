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
from beeswarm.drones.client.baits import http

from beeswarm.drones.client.baits.clientbase import ClientBase


class https(http.http, ClientBase):
    def _make_url(self, server, path, port=443):
        if port == 443:
            url = 'https://{}/{}'.format(server, path)
        else:
            url = 'https://{}:{}/{}'.format(server, port, path)
        return url
