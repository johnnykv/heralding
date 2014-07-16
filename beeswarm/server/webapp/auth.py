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
import logging
import random
import string

from werkzeug.security import generate_password_hash

from beeswarm.server.db import database_setup
from beeswarm.server.db.entities import User


logger = logging.getLogger(__name__)


class Authenticator(object):
    """ Handles server authentications """

    def ensure_default_user(self):
        session = database_setup.get_session()
        userid = 'admin'
        count = session.query(User).filter(User.id == userid).count()
        if not count:
            password = ''.join([random.choice(string.letters[:26]) for i in xrange(14)])
            pw_hash = generate_password_hash(password)
            u = User(id=userid, nickname='admin', password=pw_hash)
            session.add(u)
            session.commit()
            logger.info('Created default admin account for the beeswarm server.')
            print '****************************************************************************'
            print 'Default password for the admin account is: {0}'.format(password)
            print '****************************************************************************'

    def add_user(self, username, password, user_type, nickname=''):
        session = database_setup.get_session()
        userid = username
        pw_hash = generate_password_hash(password)
        u = User(id=userid, nickname=nickname, password=pw_hash, utype=user_type)
        session.add(u)
        session.commit()
