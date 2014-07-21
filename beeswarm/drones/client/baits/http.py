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

import random
import logging
from datetime import datetime

from lxml.html import document_fromstring
import requests
from requests.auth import HTTPBasicAuth

from beeswarm.drones.client.baits.clientbase import ClientBase


logger = logging.getLogger(__name__)


class http(ClientBase):
    def __init__(self, sessions, options):
        """
            Initializes common values.

        :param sessions: A dict which is updated every time a new session is created.
        :param options: A dict containing all options
        """
        super(http, self).__init__(sessions, options)
        self.client = requests.Session()
        self.max_requests = random.randint(3, 4)
        self.sent_requests = 0

    def start(self):

        """
            Launches a new HTTP client session on the server taken from the `self.options` dict.

        :param my_ip: IP of this Client itself
        """
        username = self.options['username']
        password = self.options['password']
        server_host = self.options['server']
        server_port = self.options['port']
        honeypot_id = self.options['honeypot_id']

        session = self.create_session(server_host, server_port, honeypot_id)

        self.sessions[session.id] = session

        logger.debug(
            'Sending {0} bait session to {1}:{2}. (bait id: {3})'.format('http', server_host, server_port, session.id))

        try:
            url = self._make_url(server_host, '/index.html', server_port)
            response = self.client.get(url, auth=HTTPBasicAuth(username, password), verify=False)
            session.did_connect = True
            if response.status_code == 200:
                session.add_auth_attempt('plaintext', True, username=username, password=password)
                session.did_login = True
            else:
                session.add_auth_attempt('plaintext', False, username=username, password=password)

            links = self._get_links(response)
            while self.sent_requests <= self.max_requests and links:
                url = random.choice(links)
                response = self.client.get(url, auth=HTTPBasicAuth(username, password), verify=False)
                links = self._get_links(response)

        except Exception as err:
            logger.debug('Caught exception: {0} ({1})'.format(err, str(type(err))))
        else:
            session.timestamp = datetime.now()
        finally:
            session.alldone = True

    def _make_url(self, server, path, port=80):
        if port == 80:
            url = 'http://{}/{}'.format(server, path)
        else:
            url = 'http://{}:{}/{}'.format(server, port, path)
        return url

    def _get_links(self, response):
        """
            Parses the response text and returns all the links in it.

        :param response: The Response object.
        """
        html_text = response.text.encode('utf-8')
        doc = document_fromstring(html_text)
        links = []
        for e in doc.cssselect('a'):
            links.append(e.get('href'))
