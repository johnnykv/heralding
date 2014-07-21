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

import mailbox
import os
import random
import smtplib
import logging
import time

import beeswarm
from beeswarm.drones.client.baits.clientbase import ClientBase


logger = logging.getLogger(__name__)


class smtp(ClientBase):
    def __init__(self, sessions, options):
        """
            Initializes common values.
        :param sessions: A dict which is updated every time a new session is created.
        :param options: A dict containing all options
        """
        super(smtp, self).__init__(sessions, options)
        self.client = None
        self.sent_mails = 0
        self.max_mails = random.randint(1, 4)
        package_dir = os.path.dirname(os.path.abspath(beeswarm.__file__))
        mbox_archive = os.path.join(package_dir, 'shared/data/archive.mbox')
        self.mailbox = mailbox.mbox(mbox_archive)

    def start(self):
        """
            Launches a new SMTP client session on the server taken from the `self.options` dict.

        :param my_ip: IP of this Client itself
        """

        username = self.options['username']
        password = self.options['password']
        server_host = self.options['server']
        server_port = self.options['port']
        honeypot_id = self.options['honeypot_id']

        session = self.create_session(server_host, server_port, honeypot_id)

        logger.debug(
            'Sending {0} bait session to {1}:{2}. (bait id: {3})'.format('smtp', server_host, server_port, session.id))

        try:
            self.connect()
            session.did_connect = True
            session.source_port = self.client.sock.getsockname()[1]
            self.login(username, password)

            # TODO: Handle failed login
            session.add_auth_attempt('plaintext', True, username=username, password=password)
            session.did_login = True

        except smtplib.SMTPException as error:
            logger.debug('Caught exception: {0} ({1})'.format(error, str(type(error))))
        else:
            while self.sent_mails <= self.max_mails:
                from_addr, to_addr, mail_body = self.get_one_mail()
                self.sent_mails += 1
                try:
                    self.client.sendmail(from_addr, to_addr, mail_body)
                except TypeError as e:
                    logger.debug('Malformed email in mbox archive, skipping.')
                    continue
                else:
                    logger.debug('Sent mail from ({0}) to ({1})'.format(from_addr, to_addr))
                time.sleep(1)
            self.client.quit()
            session.did_complete = True
        finally:
            logger.debug('SMTP Session complete.')
            session.alldone = True

    def get_one_mail(self):
        """
            Choose and return a random email from the mail archive.

        :return: Tuple containing From Address, To Address and the mail body.
        """

        while True:
            mail_key = random.choice(self.mailbox.keys())
            mail = self.mailbox[mail_key]
            from_addr = mail.get_from()
            to_addr = mail['To']
            mail_body = mail.get_payload()
            if not from_addr or not to_addr:
                continue
            return from_addr, to_addr, mail_body

    def connect(self):
        """
            Connect to the SMTP server.
        """
        self.client = smtplib.SMTP(self.options['server'], self.options['port'],
                                   local_hostname=self.options['local_hostname'], timeout=15)

    def login(self, username, password):
        """
            Login to the remote SMTP server using the specified username and password.
        :param username:
        :param password:
        """
        self.client.login(username, password)
