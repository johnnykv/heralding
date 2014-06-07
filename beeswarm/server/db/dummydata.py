# Copyright (C) 2014 Johnny Vestergaard <jkv@unixcluster.dk>
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
import string
import random
import uuid

from beeswarm.server.db.entities import Client, BaitSession, Honeypot, Authentication, Classification, Session, \
    Transcript
from beeswarm.server.db import database_setup


def fill_dummy_data():
    """
    Populates the server data with dummy data to ease development.
    """

    db_session = database_setup.get_session()

    protocols = [('pop3', 110), ('ssh', 22), ('telnet', 23), ('ftp', 21), ('http', 80)]
    source_ips = ('192.168.1.2', '192.168.2.3', '192.168.3.4', '192.168.4.5')

    honeypots = [Honeypot(id=str(uuid.uuid4()))]
    client = [Client(id=str(uuid.uuid4()))]
    sessions = []
    authentications = []

    while len(sessions) < 100:
        session = BaitSession(id=str(uuid.uuid4()), timestamp=datetime.now(),
                              source_ip=random.choice(source_ips), source_port=random.randint(1024, 65535),
                              destination_ip='4.3.2.1', destination_port='1111')

        session.protocol, session.destination_port = random.choice(protocols)
        session.honeypot = random.choice(honeypots)
        session.client = random.choice(client)
        session.classification = db_session.query(Classification).filter(Classification.type == 'bait_session').one()

        username = ''.join(random.choice(string.lowercase) for x in range(8))
        password = ''.join(random.choice(string.lowercase) for x in range(8))
        authentication = Authentication(id=str(uuid.uuid4()), username=username, password=password)
        session.authentication.append(authentication)

        for x in range(10):
            data = ''.join(random.choice(string.lowercase) for x in range(15))
            direction = ('in', 'out')[x % 2]
            transcript = Transcript(timestamp=datetime.now(), direction=direction, data=data)
            session.transcript.append(transcript)

        authentications.append(authentication)
        sessions.append(session)

    while len(sessions) < 200:
        session = Session(id=str(uuid.uuid4()), timestamp=datetime.now(),
                          source_ip=random.choice(source_ips), source_port=random.randint(1024, 65535),
                          destination_ip='4.3.2.1', destination_port='1111')

        session.protocol, session.destination_port = random.choice(protocols)
        session.honeypot = random.choice(honeypots)

        session.classification = db_session.query(Classification).filter(
            Classification.type == 'credentials_reuse').one()

        username = ''.join(random.choice(string.lowercase) for x in range(8))
        password = ''.join(random.choice(string.lowercase) for x in range(8))
        authentication = Authentication(id=str(uuid.uuid4()), username=username, password=password)
        session.authentication.append(authentication)

        authentications.append(authentication)
        sessions.append(session)

    db_session.add_all(authentications)
    db_session.add_all(sessions)
    db_session.add_all(honeypots)
    db_session.add_all(client)
    db_session.commit()


if __name__ == '__main__':
    database_setup.setup_db('sqlite:///beeswarm_sqlite.db')
    fill_dummy_data()
