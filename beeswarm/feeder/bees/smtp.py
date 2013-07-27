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
from beeswarm.feeder.bees.clientbase import ClientBase


class smtp(ClientBase):

    def __init__(self, sessions, options):
        super(smtp, self).__init__(sessions, options)
        self.client = None
        self.sent_mails = 0
        self.max_mails = random.randint(1, 4)
        package_dir = os.path.dirname(os.path.abspath(beeswarm.__file__))
        mbox_archive = os.path.join(package_dir, 'shared/data/archive.mbox')
        self.mailbox = mailbox.mbox(mbox_archive)

    def do_session(self, my_ip):

        login = self.options['login']
        password = self.options['password']
        server_host = self.options['server']
        server_port = self.options['port']

        session = self.create_session(login, password, server_host, server_port, my_ip)

        logging.debug(
            'Sending %s honeybee to %s:%s. (bee id: %s)' % ('smtp', server_host, server_port, session.id))

        try:
            self.client = smtplib.SMTP(server_host, server_port, local_hostname=self.options['local_hostname'],
                                       timeout=15)
            session.source_port = self.client.sock.getsockname()[1]
            session.did_connect = True
            self.client.login(login, password)
            session.did_login = True
        except smtplib.SMTPException as error:
            logging.debug('Caught exception: %s (%s)' % (error, str(type(error))))
        else:
            while self.sent_mails <= self.max_mails:
                from_addr, to_addr, mail_body = self.get_one_mail()
                try:
                    self.client.sendmail(from_addr, to_addr, mail_body)
                except TypeError as e:
                    logging.debug('Malformed email in mbox archive, skipping.')
                    continue
                else:
                    logging.debug('Sent mail from (%s) to (%s)' % (from_addr, to_addr))
                time.sleep(1)
            self.client.quit()
            session.did_complete = True
        finally:
            logging.debug('SMTP Session complete.')
            session.alldone = True

    def get_one_mail(self):
        mail_key = random.choice(self.mailbox.keys())
        mail = self.mailbox[mail_key]
        from_addr = mail.get_from()
        to_addr = mail['To']
        mail_body = mail.get_payload()
        return from_addr, to_addr, mail_body
