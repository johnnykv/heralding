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

import os
import json
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from entities import Classification
from entities import BaitUser
import entities


DB_Session = None
engine = None

logger = logging.getLogger(__name__)


def setup_db(connection_string):
    """
        Sets up the database schema and adds defaults.
    :param connection_string: Database URL. e.g: sqlite:///filename.db
                              This is usually taken from the config file.
    """
    global DB_Session, engine
    engine = create_engine(connection_string)
    entities.Base.metadata.create_all(engine)
    DB_Session = sessionmaker(bind=engine)
    db_path = os.path.dirname(__file__)

    # bootstrapping the db with classifications types
    json_file = open(os.path.join(db_path, 'bootstrap.json'))
    data = json.load(json_file)
    session = get_session()
    for entry in data['classifications']:
        c = session.query(Classification).filter(Classification.type == entry['type']).first()
        if not c:
            classification = Classification(type=entry['type'], description_short=entry['description_short'],
                                            description_long=entry['description_long'])
            session.add(classification)
        else:
            c.description_short = entry['description_short']
            c.description_long = entry['description_long']
    for username in data['bait_users']:
        u = session.query(BaitUser).filter(BaitUser.username == username).first()
        if not u:
            logger.debug('Creating default BaitUser: {}'.format(username))
            password = data['bait_users'][username]
            huser = BaitUser(username=username, password=password)
            session.add(huser)
    session.commit()


def clear_db():
    entities.Base.metadata.drop_all(engine)


def get_session():
    if DB_Session:
        return DB_Session()
    else:
        raise Exception('DB session has not been configured, please run setup_db.')
