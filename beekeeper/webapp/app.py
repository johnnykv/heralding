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

from datetime import datetime
import json
from flask import Flask, render_template, request
from pony.orm import commit, select
from beekeeper.database import feeder, honeybee
from beekeeper.database import session as Session

app = Flask(__name__)
app.config['DEBUG'] = True


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/sessions')
def sessions_all():
    sessions = select(s for s in Session)
    return render_template('logs.html', sessions=sessions)


@app.route('/sessions/honeybees')
def sessions_honeybees():
    honeybees = select(h for h in honeybee)
    return render_template('logs.html', sessions=honeybees)

@app.route('/sessions/attacks')
def sessions_attacks():
    #TODO: Figure out the correct way to do this with PonyORM
    attacks = select(a for a in Session if a.classtype is None)
    return render_template('logs.html', sessions=attacks)

@app.route('/ws/feeder_data', methods=['POST'])
def feeder_data():
    #TODO: investigate why the flask provided request.json returns None.
    data = json.loads(request.data)

    #the passed json dict will include these items in the future. (issue #51)
    source_ip = 'a'
    source_port = 0

    _feeder = feeder.get(id=data['feeder_id'])
    #create if not found in the database
    if not _feeder:
        _feeder = feeder(id=data['feeder_id'])

    _honeybee = honeybee(id=data['id'],
                         timestamp=datetime.strptime(data['timestamp'], '%Y-%m-%dT%H:%M:%S.%f'),
                         protocol=data['protocol'],
                         username=data['login'],
                         password=data['password'],
                         destination_ip=data['server_host'],
                         destination_port=data['server_port'],
                         source_ip=source_ip,
                         source_port=source_port,
                         did_connect=data['did_connect'],
                         did_login=data['did_login'],
                         did_complete=data['did_complete'],
                         feeder=_feeder)

    commit()

    return ''


if __name__ == '__main__':
    app.run()
