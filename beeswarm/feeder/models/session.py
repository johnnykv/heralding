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

from datetime import datetime
from beeswarm.shared.models.base_session import BaseSession


class BeeSession(BaseSession):

    feeder_id = ''
    hive_id = ''

    def __init__(self, protocol, destination_ip, destination_port, my_ip):
        super(BeeSession, self).__init__(protocol, source_ip=my_ip, destination_ip=destination_ip,
                                         destination_port=destination_port)

        assert BeeSession.feeder_id

        self.feeder_id = BeeSession.feeder_id
        self.hive_id = BeeSession.hive_id

        self.did_connect = False
        self.did_login = False
        self.alldone = False
        self.did_complete = False
        self.protocol_data = {}

    def to_dict(self):
        return vars(self)
