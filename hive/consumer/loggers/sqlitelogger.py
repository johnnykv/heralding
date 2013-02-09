# Copyright (C) 2012 Johnny Vestergaard <jkv@unixcluster.dk>
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

import sqlite3
from os import path

from loggerbase import LoggerBase


class SqliteLogger(LoggerBase):
    db_name = 'hive_sqlite.db'

    def log(self, session):
        if not path.exists(SqliteLogger.db_name):
            self.create_db()

        conn = sqlite3.connect(SqliteLogger.db_name)
        cursor = conn.cursor()

        session_tuple = (str(session['id']), session['timestamp'],
                         session['last_activity'], session['protocol'],
                         session['protocol_port'], session['attacker_ip'],
                         session['attacker_src_port'])

        cursor.execute('INSERT INTO sessions VALUES (?,?,?,?,?,?,?)', session_tuple)

        auth_tuples = []

        for auth in session['login_tries']:
            auth_tuples.append((str(auth['id']), str(session['id']),
                                auth['timestamp'], auth['login'],
                                auth['password']))

        cursor.executemany('INSERT INTO auth_attempts VALUES (?,?,?,?,?)', auth_tuples)

        conn.commit()


    def create_db(self):
        conn = sqlite3.connect(SqliteLogger.db_name)
        cursor = conn.cursor()
        cursor.execute("""
			CREATE TABLE IF NOT EXISTS sessions(
				session_id TEXT PRIMARY KEY NOT NULL,
				timestamp_start TEXT NOT NULL,
				timestamp_end TEXT NOT NULL,
				protocol TEXT NOT NULL,
				protocol_port TEXT NOT NULL,
				attacker_ip TEXT NOT NULL,
				attacker_src_port TEXT NOT NULL)
				""")

        cursor.execute("""
			CREATE TABLE IF NOT EXISTS auth_attempts(
				auth_id TEXT PRIMARY KEY NOT NULL,
				fk_session_id TEXT NOT NULL,
				timestamp TEXT NOT NULL,
				login TEXT NOT NULL,
				password TEXT NOT NULL,
				FOREIGN KEY(fk_session_id) REFERENCES sessions(session_id))
				""")
        conn.commit()

        # session = {'id' : uuid.uuid4(),  				#OK
        # 		   'timestamp' : datetime.utcnow(),		#OK
        # 		   'last_activity' : datetime.utcnow(),	#OK
        # 		   'address' : address,					#OK
        # 		   'connected' : True,
        # 		   'port' : pop3.port,
        # 		   'protocol' : 'pop3',
        # 		   'login_tries' : []}