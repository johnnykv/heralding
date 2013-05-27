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
import logging
from flask import Flask, render_template, request, abort
from pony.orm import commit, select
from beeswarm.beekeeper.db.database import Feeder, Honeybee, Session, Hive, Classification

app = Flask(__name__)
app.config['DEBUG'] = True

logger = logging.getLogger(__name__)

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/sessions')
def sessions_all():
    sessions = select(s for s in Session)
    return render_template('logs.html', sessions=sessions)


@app.route('/sessions/honeybees')
def sessions_honeybees():
    honeybees = select(h for h in Honeybee)
    return render_template('logs.html', sessions=honeybees)

@app.route('/sessions/attacks')
def sessions_attacks():
    #TODO: Figure out the correct way to do this with PonyORM
    attacks = select(a for a in Session if a.classtype == 'Session')
    return render_template('logs.html', sessions=attacks)

@app.route('/ws/feeder_data', methods=['POST'])
def feeder_data():
    #TODO: investigate why the flask provided request.json returns None.
    data = json.loads(request.data)

    _feeder = Feeder.get(id=data['feeder_id'])

    _honeybee = Honeybee(id=data['id'],
                         timestamp=datetime.strptime(data['timestamp'], '%Y-%m-%dT%H:%M:%S.%f'),
                         received=datetime.utcnow(),
                         protocol=data['protocol'],
                         username=data['login'],
                         password=data['password'],
                         destination_ip=data['server_host'],
                         destination_port=data['server_port'],
                         source_ip=data['source_ip'],
                         source_port=data['source_port'],
                         did_connect=data['did_connect'],
                         did_login=data['did_login'],
                         did_complete=data['did_complete'],
                         feeder=_feeder)

    commit()

    return ''

@app.route('/ws/hive_data', methods=['POST'])
def hive_data():
    #TODO: investigate why the flask provided request.json returns None.
    data = json.loads(request.data)
    logger.debug('Received: {0}'.format(data))

    _hive = Hive.get(id=data['hive_id'])
    #create if not found in the database

    for login_attempt in data['login_attempts']:
        _session = Session(id=login_attempt['id'],
                           timestamp=datetime.strptime(login_attempt['timestamp'], '%Y-%m-%dT%H:%M:%S.%f'),
                           received=datetime.utcnow(),
                           protocol=data['protocol'],
                           #TODO: not all capabilities delivers login/passwords. This needs to be subclasses...
                           username=login_attempt['username'],
                           password=login_attempt['password'],
                           destination_ip='aaa',
                           destination_port=data['honey_port'],
                           source_ip=data['attacker_ip'],
                           source_port=data['attacker_source_port'],
                           hive=_hive)

    commit()
    return ''

if __name__ == '__main__':
    app.run()
