# Copyright (C) 2013 Johnny Vestergaard <jkv@unixcluster.dk>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
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
import tempfile
import urlparse
import uuid
import json
from datetime import datetime
from lxml import html

import requests
from requests.exceptions import RequestException
from beeswarm.client.consumer.loggers.loggerbase import LoggerBase

logger = logging.getLogger(__name__)


class Server(LoggerBase):
    def __init__(self, config):
        super(Server, self).__init__(config)
        self.config = config
        self.server_url = self.config['log_server']['server_url']
        self.submit_url = urlparse.urljoin(self.server_url, 'ws/client_data')
        self.tempcert = tempfile.NamedTemporaryFile()
        self.tempcert.write(config['log_server']['cert'])
        self.tempcert.flush()
        self._login()

    def log(self, session):
        try:
            data = json.dumps(session.to_dict(), default=json_default)
            response = self.websession.post(self.submit_url, data=data, verify=self.tempcert.name, allow_redirects=False)
            #raise exception for everything other than response code 200
            response.raise_for_status()
            # also raise for 302
            if response.status_code == 302:
                raise RequestException()
        except RequestException as ex:
            logger.error('Error sending data to server: {0}'.format(ex))

    def _login(self):
        logger.info('Connecting to Beeswarm server.')
        self.websession = requests.session()
        login_url = urlparse.urljoin(self.server_url, 'login')
        csrf_response = self.websession.get(login_url, verify=self.tempcert.name)
        csrf_doc = html.document_fromstring(csrf_response.text)
        csrf_token = csrf_doc.get_element_by_id('csrf_token').value
        login_data = {
            'username': self.config['general']['client_id'],
            'password': self.config['log_server']['server_pass'],
            'csrf_token': csrf_token,
            'submit': ''
        }
        headers = {
            'Referer': login_url
        }
        self.websession.post(login_url, data=login_data, headers=headers, verify=self.tempcert.name)

def json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, uuid.UUID):
        return str(obj)
    else:
        return None