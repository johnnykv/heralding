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

import json
import logging
import random
import string
import ast
import gevent
import gevent.lock
import os
import uuid
import zmq.green as zmq
from flask import Flask, render_template, redirect, flash, Response, abort
from flask.ext.login import LoginManager, login_user, current_user, login_required, logout_user, UserMixin
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
from wtforms import HiddenField
from flask import request

from forms import HoneypotConfigurationForm, ClientConfigurationForm, LoginForm, SettingsForm
from beeswarm.shared.message_enum import Messages
from beeswarm.shared.socket_enum import SocketNames
import beeswarm


def is_hidden_field_filter(field):
    return isinstance(field, HiddenField)


app = Flask(__name__)
app.config['DEBUG'] = False
app.config['WTF_CSRF_ENABLED'] = True
app.config['SECRET_KEY'] = ''.join(random.choice(string.lowercase) for x in range(random.randint(16, 32)))
app.jinja_env.filters['bootstrap_is_hidden_field'] = is_hidden_field_filter

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

logger = logging.getLogger(__name__)

first_cfg_received = gevent.event.Event()

# keys used for adding new drones to the system
drone_keys = []

config_actor_socket = None
database_actor_socket = None
config_request_lock = gevent.lock.RLock()
database_request_lock = gevent.lock.RLock()
admin_passwd_file = 'admin_passwd_hash'


def connect_sockets():
    global config_actor_socket, database_actor_socket
    if config_actor_socket is not None:
        config_actor_socket.disconnect(SocketNames.CONFIG_COMMANDS.value)
    if database_actor_socket is not None:
        database_actor_socket.disconnect(SocketNames.DATABASE_REQUESTS.value)

    context = beeswarm.shared.zmq_context
    config_actor_socket = context.socket(zmq.REQ)
    database_actor_socket = context.socket(zmq.REQ)

    config_actor_socket.connect(SocketNames.CONFIG_COMMANDS.value)
    database_actor_socket.connect(SocketNames.DATABASE_REQUESTS.value)


connect_sockets()


def send_zmq_request_socket(socket, _request):
    socket.send(_request)
    result = socket.recv()
    status, data = result.split(' ', 1)
    if status != Messages.OK.value:
        logger.error('Receiving actor on socket {0} failed to respond properly. The request was: {1}'.format(socket,
                                                                                                             _request))
        if data:
            abort(500, data)
        else:
            abort(500)
    else:
        if data.startswith('{') or data.startswith('['):
            return json.loads(result.split(' ', 1)[1])
        else:
            return data


def send_database_request(database_request):
    database_request_lock.acquire()
    try:
        return send_zmq_request_socket(database_actor_socket, database_request)
    finally:
        database_request_lock.release()


def send_config_request(config_request):
    config_request_lock.acquire()
    try:
        return send_zmq_request_socket(config_actor_socket, config_request)
    finally:
        config_request_lock.release()


def ensure_admin_password(reset_password, password=None):
    global admin_passwd_hash
    if not os.path.isfile(admin_passwd_file) or reset_password:
        if not password:
            password = ''.join([random.choice(string.letters[:26]) for i in xrange(14)])
        password_hash = generate_password_hash(password)
        with os.fdopen(os.open(admin_passwd_file, os.O_WRONLY | os.O_CREAT, 0600), 'w') as _file:
            _file.truncate()
            _file.write(password_hash)

        logger.info('Created default admin account for the beeswarm server, password has been '
                    'printed to the console.')
        print '****************************************************************************'
        print 'Password for the admin account is: {0}'.format(password)
        print '****************************************************************************'


class User(UserMixin):
    def __init__(self, user_name):
        self.id = user_name


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user_name = 'admin'
        with open(admin_passwd_file, 'r') as _file:
            password_hash = _file.read()
        if check_password_hash(password_hash, form.password.data):
            user = User(user_name)
            login_user(user)
            logger.info('User {0} logged in.'.format(user_name))
            flash('Logged in successfully')
            return redirect(request.args.get("next") or '/')
    return render_template('login.html', form=form)


@app.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    flash('Logged out succesfully')
    return redirect('/login')


@login_manager.user_loader
def load_user(userid):
    return User('admin')


@app.route('/')
@login_required
def home():
    database_stats = send_database_request('{0}'.format(Messages.GET_DB_STATS.value))
    return render_template('index.html', user=current_user, status=database_stats)


@app.route('/bait_users')
@login_required
def bait_users_route():
    return render_template('bait_users.html', user=current_user)


@app.route('/sessions')
@login_required
def sessions_all():
    return render_template('logs.html', logtype='All', user=current_user)


@app.route('/sessions/bait_sessions')
@login_required
def sessions_bait():
    return render_template('logs.html', logtype='BaitSessions', user=current_user)


@app.route('/sessions/attacks')
@login_required
def sessions_attacks():
    return render_template('logs.html', logtype='Attacks', user=current_user)


class DictWrapper():
    def __init__(self, data):
        self.data = data

    def __getattr__(self, name):
        path = name.split('__')
        result = self._rec(path, self.data)
        return result

    def _rec(self, path, item):
        if len(path) == 1:
            return item[path[0]]
        else:
            return self._rec(path[1:], item[path[0]])


@app.route('/ws/drone/honeypot/configure/<drone_id>', methods=['GET', 'POST'])
@login_required
def configure_honeypot(drone_id):
    config_dict = send_database_request('{0} {1}'.format(Messages.DRONE_CONFIG.value, drone_id))

    config_obj = DictWrapper(config_dict)
    form = HoneypotConfigurationForm(obj=config_obj)
    if not form.validate_on_submit():
        return render_template('configure-honeypot.html', form=form, mode_name='Honeypot', user=current_user)
    else:
        # TODO: We really need to user protobuf, thrift or something like that for stuff like this.
        honeypot_config = {
            'name': form.general__name.data,
            'mode': 'honeypot',
            'certificate': {
                'common_name': form.certificate_info__common_name.data,
                'country': form.certificate_info__country.data,
                'state': form.certificate_info__state.data,
                'locality': form.certificate_info__locality.data,
                'organization': form.certificate_info__organization.data,
                'organization_unit': form.certificate_info__organization_unit.data
            },
            'capabilities': {}
        }

        if form.capabilities__ftp__enabled.data:
            honeypot_config['capabilities']['ftp'] = {
                'port': form.capabilities__ftp__port.data,
                'protocol_specific_data': {
                    'max_attempts': form.capabilities__ftp__protocol_specific_data__max_attempts.data,
                    'banner': form.capabilities__ftp__protocol_specific_data__banner.data,
                    'syst_type': form.capabilities__ftp__protocol_specific_data__syst_type.data
                }}

        if form.capabilities__telnet__enabled.data:
            honeypot_config['capabilities']['telnet'] = {
                'port': form.capabilities__telnet__port.data,
                'protocol_specific_data': {
                    'max_attempts': form.capabilities__telnet__protocol_specific_data__max_attempts.data,
                }}

        if form.capabilities__pop3__enabled.data:
            honeypot_config['capabilities']['pop3'] = {
                'port': form.capabilities__pop3__port.data,
                'protocol_specific_data': {
                    'max_attempts': form.capabilities__pop3__protocol_specific_data__max_attempts.data,
                }}

        if form.capabilities__pop3s__enabled.data:
            honeypot_config['capabilities']['pop3s'] = {
                'port': form.capabilities__pop3s__port.data,
                'protocol_specific_data': {
                    'max_attempts': form.capabilities__pop3s__protocol_specific_data__max_attempts.data,
                }}

        if form.capabilities__ssh__enabled.data:
            honeypot_config['capabilities']['ssh'] = {
                'port': form.capabilities__ssh__port.data
            }

        if form.capabilities__http__enabled.data:
            honeypot_config['capabilities']['http'] = {
                'port': form.capabilities__http__port.data,
                'protocol_specific_data': {
                    'banner': form.capabilities__http__protocol_specific_data__banner.data,
                }
            }

        if form.capabilities__https__enabled.data:
            honeypot_config['capabilities']['https'] = {
                'port': form.capabilities__https__port.data,
                'protocol_specific_data': {
                    'banner': form.capabilities__https__protocol_specific_data__banner.data,
                }
            }
        if form.capabilities__smtp__enabled.data:
            honeypot_config['capabilities']['smtp'] = {
                'port': form.capabilities__smtp__port.data,
                'protocol_specific_data': {
                    'banner': form.capabilities__smtp__protocol_specific_data__banner.data
                }
            }
        if form.capabilities__vnc__enabled.data:
            honeypot_config['capabilities']['vnc'] = {
                'port': form.capabilities__vnc__port.data,
                'protocol_specific_data': {}
            }

        send_database_request('{0} {1} {2}'.format(Messages.CONFIG_DRONE.value, drone_id,
                                                   json.dumps(honeypot_config)))
        return render_template('finish-config-honeypot.html', drone_id=drone_id, user=current_user)


@app.route('/ws/drone/client/configure/<drone_id>', methods=['GET', 'POST'])
@login_required
def configure_client(drone_id):
    config_dict = send_database_request('{0} {1}'.format(Messages.DRONE_CONFIG.value, drone_id))
    config_obj = DictWrapper(config_dict)
    form = ClientConfigurationForm(obj=config_obj)
    if not form.validate_on_submit():
        return render_template('configure-client.html', form=form, mode_name='Client', user=current_user)
    else:
        bait_timing_config = {
                         'mode': 'client'}
            'http': {
                'active_range': form.bait_timings__http__active_range.data,
                'sleep_interval': form.bait_timings__http__sleep_interval.data,
                'activation_probability': form.bait_timings__http__activation_probability.data
            },
            'ftp': {
                'active_range': form.bait_timings__ftp__active_range.data,
                'sleep_interval': form.bait_timings__ftp__sleep_interval.data,
                'activation_probability': form.bait_timings__ftp__activation_probability.data
            },
            'https': {
                'active_range': form.bait_timings__https__active_range.data,
                'sleep_interval': form.bait_timings__https__sleep_interval.data,
                'activation_probability': form.bait_timings__https__activation_probability.data
            },
            'pop3': {
                'active_range': form.bait_timings__pop3__active_range.data,
                'sleep_interval': form.bait_timings__pop3__sleep_interval.data,
                'activation_probability': form.bait_timings__pop3__activation_probability.data
            },
            'ssh': {
                'active_range': form.bait_timings__ssh__active_range.data,
                'sleep_interval': form.bait_timings__ssh__sleep_interval.data,
                'activation_probability': form.bait_timings__ssh__activation_probability.data
            },
            'pop3s': {
                'active_range': form.bait_timings__pop3s__active_range.data,
                'sleep_interval': form.bait_timings__pop3s__sleep_interval.data,
                'activation_probability': form.bait_timings__pop3s__activation_probability.data
            },
            'smtp': {
                'active_range': form.bait_timings__smtp__active_range.data,
                'sleep_interval': form.bait_timings__smtp__sleep_interval.data,
                'activation_probability': form.bait_timings__smtp__activation_probability.data
            },
            'vnc': {
                'active_range': form.bait_timings__vnc__active_range.data,
                'sleep_interval': form.bait_timings__vnc__sleep_interval.data,
                'activation_probability': form.bait_timings__vnc__activation_probability.data
            },
            'telnet': {
                'active_range': form.bait_timings__telnet__active_range.data,
                'sleep_interval': form.bait_timings__telnet__sleep_interval.data,
                'activation_probability': form.bait_timings__telnet__activation_probability.data
            }
        }

        send_database_request('{0} {1} {2}'.format(Messages.CONFIG_DRONE.value, drone_id,
                                                   json.dumps(bait_timing_config)))
        return render_template('finish-config-client.html', drone_id=drone_id, user=current_user)


@app.route('/ws/drone/configure/<drone_id>', methods=['GET', 'POST'])
@login_required
def configure_drone(drone_id):
    return render_template('drone_mode.html', drone_id=drone_id, user=current_user)


def reset_drone_key(key):
    global drone_keys
    if key in drone_keys:
        drone_keys.remove(key)
        logger.debug('Removed drone add key.')
    else:
        logger.debug('Tried to remove drone key, but the key was not found.')


@app.route('/ws/drone/add', methods=['GET'])
@login_required
def add_drone():
    global drone_keys
    drone_key = str(uuid.uuid4())
    drone_keys.append(drone_key)
    # remove drone key after 120 seconds
    gevent.spawn_later(120, reset_drone_key, drone_key)

    server_host = send_config_request('{0} {1}'.format(Messages.GET_CONFIG_ITEM.value, 'network,server_host'))
    server_web_port = send_config_request('{0} {1}'.format(Messages.GET_CONFIG_ITEM.value, 'network,web_port'))
    server_https = 'https://{0}:{1}/'.format(server_host, server_web_port)
    drone_link = '{0}ws/drone/add/{1}'.format(server_https, drone_key)
    return render_template('add_drone.html', user=current_user, drone_link=drone_link)


# TODO: throttle this
@app.route('/ws/drone/add/<key>', methods=['GET'])
def drone_key(key):
    global drone_keys
    if key not in drone_keys:
        logger.warn('Attempt to add new drone, but using wrong key from: {0}'.format(request.remote_addr))
        abort(401)
    else:
        drone_config = send_database_request('{0}'.format(Messages.DRONE_ADD.value))
        return json.dumps(drone_config)


@app.route('/ws/drone/delete', methods=['POST'])
@login_required
def delete_drones():
    # list of drone id's'
    drone_ids = json.loads(request.data)
    for drone_id in drone_ids:
        send_database_request('{0} {1}'.format(Messages.DRONE_DELETE.value, drone_id))
    return ''


@app.route('/ws/bait_users', methods=['GET', 'POST'])
@login_required
def get_bait_users():
    if request.method == 'GET':
        bait_users = send_database_request('{0}'.format(Messages.GET_BAIT_USERS.value))
        rsp = Response(response=json.dumps(bait_users), status=200, mimetype='application/json')
        return rsp
    return ''


# add a list of bait users, if user exists the password will be replaced with the new one
@app.route('/ws/bait_users/add', methods=['POST'])
@login_required
def add_bait_users():
    bait_users = json.loads(request.data)
    for bait_user in bait_users:
        # TODO: Also validate client side
        if bait_user['username'] == '':
            continue
        send_database_request(
            '{0} {1} {2}'.format(Messages.BAIT_USER_ADD.value, bait_user['username'], bait_user['password']))
    return ''


# deletes a single bait user or a list of users
@app.route('/ws/bait_users/delete', methods=['POST'])
@login_required
def delete_bait_user():
    # list of bait user id's
    bait_users = json.loads(request.data)
    for _id in bait_users:
        send_database_request('{0} {1}'.format(Messages.BAIT_USER_DELETE.value, _id))
    return ''


@app.route('/data/sessions/<_type>', methods=['GET'])
@login_required
def data_sessions_attacks(_type):
    sessions = []
    if _type == 'all':
        sessions = send_database_request('{0}'.format(Messages.GET_SESSIONS_ALL.value))
    elif _type == 'bait_sessions':
        sessions = send_database_request('{0}'.format(Messages.GET_SESSIONS_BAIT.value))
    elif _type == 'attacks':
        sessions = send_database_request('{0}'.format(Messages.GET_SESSIONS_ATTACKS.value))
    rsp = Response(response=json.dumps(sessions), status=200, mimetype='application/json')
    return rsp


@app.route('/data/session/<_id>/credentials')
@login_required
def data_session_credentials(_id):
    credentials = send_database_request('{0} {1}'.format(Messages.GET_SESSION_CREDENTIALS.value, _id))
    rsp = Response(response=json.dumps(credentials), status=200, mimetype='application/json')
    return rsp


@app.route('/data/session/<_id>/transcript')
@login_required
def data_session_transcript(_id):
    transcript = send_database_request('{0} {1}'.format(Messages.GET_SESSION_TRANSCRIPT.value, _id))
    rsp = Response(response=json.dumps(transcript), status=200, mimetype='application/json')
    return rsp


@app.route('/data/drones', defaults={'drone_type': None}, methods=['GET'])
@app.route('/data/drones/<drone_type>', methods=['GET'])
@login_required
def data_drones(drone_type):
    drone_list = send_database_request('{0} {1}'.format(Messages.GET_DRONE_LIST.value, drone_type))
    rsp = Response(response=json.dumps(drone_list), status=200, mimetype='application/json')
    return rsp


@app.route('/ws/drones', defaults={'drone_type': 'all'})
@app.route('/ws/drones/<drone_type>')
@login_required
def drones(drone_type):
    return render_template('drones.html', user=current_user, dronetype=drone_type)


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    bait_session_retain = send_config_request('{0} {1}'.format(Messages.GET_CONFIG_ITEM.value, 'bait_session_retain'))
    ignore_failed_bait_session = ast.literal_eval(send_config_request('{0} {1}'.format(Messages.GET_CONFIG_ITEM.value,
                                                                                       'ignore_failed_bait_session')))
    malicious_session_retain = send_config_request('{0} {1}'.format(Messages.GET_CONFIG_ITEM.value,
                                                                    'malicious_session_retain'))
    form = SettingsForm(bait_session_retain=bait_session_retain, malicious_session_retain=malicious_session_retain,
                        ignore_failed_bait_session=ignore_failed_bait_session)

    if form.validate_on_submit():
        # the potential updates that we want to save to config file.
        options = {'bait_session_retain': form.bait_session_retain.data,
                   'malicious_session_retain': form.malicious_session_retain.data,
                   'ignore_failed_bait_session': form.ignore_failed_bait_session.data}
        send_config_request('{0} {1}'.format(Messages.SET_CONFIG_ITEM.value, json.dumps(options)))
    return render_template('settings.html', form=form, user=current_user)


if __name__ == '__main__':
    app.run()
