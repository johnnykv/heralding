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
import uuid
import json
from datetime import datetime

import requests
from requests.exceptions import RequestException
from loggerbase import LoggerBase

logger = logging.getLogger(__name__)


class Beekeeper(LoggerBase):
    def __init__(self, config):
        super(Beekeeper, self).__init__(config)
        self.beekeeper_url = self.config.get('beekeeper', 'beekeeper_url')

    def log(self, session):
        try:
            data = json.dumps(session.to_dict(), default=json_default)
            response = requests.post(self.beekeeper_url, data=data)
            #raise exception for everything other than response code 200
            response.raise_for_status()
        except RequestException as ex:
            logger.error('Error sending data to beekeeper: {0}'.format(ex))


def json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, uuid.UUID):
        return str(obj)
    else:
        return None