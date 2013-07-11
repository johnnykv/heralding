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
import urlparse
import uuid
import json
from datetime import datetime

import requests
from lxml import html
from requests.exceptions import RequestException
from beeswarm.hive.consumer.loggers.loggerbase import LoggerBase

logger = logging.getLogger(__name__)


class Beekeeper(LoggerBase):
    def __init__(self, config):
        super(Beekeeper, self).__init__(config)
        self.beekeeper_url = config['log_beekeeper']['beekeeper_url']
        self.submit_url = urlparse.urljoin(self.beekeeper_url, 'ws/hive')
        self.websession = requests.session()
        login_url = urlparse.urljoin(self.beekeeper_url, 'login')
        csrf_response = self.websession.get(login_url, verify=False)
        csrf_doc = html.document_fromstring(csrf_response.text)
        csrf_token = csrf_doc.get_element_by_id('csrf_token').value
        login_data = {
            'username': config['general']['hive_id'],
            'password': config['log_beekeeper']['beekeeper_pass'],
            'csrf_token': csrf_token,
            'submit': ''
        }
        headers = {
            'Referer': login_url
        }
        self.websession.post(login_url, data=login_data, headers=headers, verify=False)

    def log(self, session):
        try:
            data = json.dumps(session.to_dict(), default=json_default)
            response = self.websession.post(self.submit_url, data=data, verify=False)
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
