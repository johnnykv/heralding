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

import smtplib
import logging
from clientbase import ClientBase


class smtp(ClientBase):

    def __init__(self, sessions):
        super(smtp, self).__init__(sessions)

    def do_session(self, login, password, server_host, server_port, my_ip):

        from_addr = 'ned@stark.com'
        to_addr = 'jon@snow.com'
        mail_body = 'Winter is coming!'

        session = self.create_session(login, password, server_host, server_port, my_ip)

        logging.debug(
            'Sending %s honeybee to %s:%s. (bee id: %s)' % ('smtp', server_host, server_port, session.id))

        try:
            #TODO local_hostname could be made configurable, from the config file
            smtp_ = smtplib.SMTP(server_host, server_port, local_hostname='localhost', timeout=15)
            session.did_connect = True
            smtp_.login(login, password)
            session.did_login = True
        except smtplib.SMTPException as error:
            logging.debug('Caught exception: %s (%s)' % (error, str(type(error))))
        else:
            smtp_.sendmail(from_addr, to_addr, mail_body)
            smtp_.quit()
            session.did_complete = True
        finally:
            session.alldone = True
