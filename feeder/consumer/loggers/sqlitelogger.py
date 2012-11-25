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
from loggerbase import LoggerBase
from os import path

class SqliteLogger(LoggerBase):
	db_name = 'feeder_sqlite.db'

	def log(self, session):
		if not path.exists(SqliteLogger.db_name):
			self.create_db()
		
		conn = sqlite3.connect(SqliteLogger.db_name)
		cursor = conn.cursor()
		
		session_tuple = (str(session['id']), session['protocol'], session['my_ip'], 
						 session['login'], session['password'], session['server_host'],
						 session['server_port'], session['timestamp'], session['did_connect'],
						 session['did_login'], session['did_complete'])

		cursor.execute('INSERT INTO honeybees VALUES (?,?,?,?,?,?,?,?,?,?,?)', session_tuple)

		conn.commit()


	def create_db(self):
		conn = sqlite3.connect(SqliteLogger.db_name)
		cursor = conn.cursor()
		cursor.execute("""
			CREATE TABLE IF NOT EXISTS honeybees(
				id TEXT PRIMARY KEY NOT NULL,
				protocol TEXT NOT null,
				my_ip TEXT NOT null,
				login TEXT NOT null,
				password TEXT NOT null,
				server_host TEXT NOT null,
				server_port TEXT NOT null,
				timestamp TEXT NOT null,
				did_connect TEXT NOT null,
				did_login TEXT NOT null,
				did_complete TEXT NOT null)
				""")

		conn.commit()

		# session = {
		# 		   'id' : uuid.uuid4(),
		# 		   'protocol' : 'pop3',
		# 		   'my_ip' : my_ip,
		# 		   'login' : login,
		# 		   'password' : password,
		# 		   'server_host' : server_host,
		# 		   'server_port' : server_port,
		# 		   'timestamp' : datetime.utcnow(),
		# 		   'did_connect' : False,
		# 		   'did_login' : False,
		# 		   'did_complete' : False,
		# 		   'protocol_data' : {}
