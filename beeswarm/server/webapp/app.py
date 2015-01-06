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
import zmq.green as zmq
from flask import Flask, render_template, redirect, flash, Response, abort
from flask.ext.login import LoginManager, login_user, current_user, login_required, logout_user
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.security import check_password_hash
from wtforms import HiddenField
from flask import request

from beeswarm.server.webapp.auth import Authenticator
from forms import HoneypotConfigurationForm, ClientConfigurationForm, LoginForm, SettingsForm
from beeswarm.server.db import database_setup
from beeswarm.server.db.entities import Client, Honeypot, User, Drone
from beeswarm.shared.helpers import send_zmq_request_socket
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

authenticator = Authenticator()
first_cfg_received = gevent.event.Event()

# keys used for adding new drones to the system
drone_keys = []

config_actor_socket = None
database_actor_socket = None
config_request_lock = gevent.lock.RLock()
database_request_lock = gevent.lock.RLock()


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

@login_manager.user_loader
def user_loader(user_id):
    user_id = user_id.encode('utf-8')
    # TODO: No need for this to be stored in session database, could just be a file...
    db_session = database_setup.get_session()
    user = None
    try:
        user = db_session.query(User).filter(User.id == user_id).one()
    except NoResultFound:
        logger.info('Attempt to load non-existent user: {0}'.format(user_id))
    return user


@app.route('/')
@login_required
def home():
    database_stats = send_database_request('{0}'.format(Messages.GET_DB_STATS.value))
    return render_template('index.html', user=current_user, status=database_stats)

@app.route('/bait_users')
@login_required
def bait_users():
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


@app.route('/ws/drone/honeypot/<drone_id>')
@login_required
def set_honeypot_mode(drone_id):
    db_session = database_setup.get_session()
    drone = db_session.query(Drone).filter(Drone.id == drone_id).one()
    if drone is None or drone.discriminator != 'honeypot':
        # meh, better way do do this?
        db_session.delete(drone)
        db_session.commit()
        honeypot = Honeypot(id=drone_id)
        honeypot.ip_address = drone.ip_address
        db_session.add(honeypot)
        db_session.commit()
        return ''
    else:
        return ''


@app.route('/ws/drone/client/<drone_id>')
@login_required
def set_client_mode(drone_id):
    db_session = database_setup.get_session()
    drone = db_session.query(Drone).filter(Drone.id == drone_id).one()
    if drone is None or drone.discriminator != 'client':
        # meh, better way do do this?
        db_session.delete(drone)
        db_session.commit()
        client = Client(id=drone_id)
        client.ip_address = drone.ip_address
        db_session.add(client)
        db_session.commit()
        return ''
    else:
        return ''


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


@app.route('/ws/drone/honeypot/configure/<id>', methods=['GET', 'POST'])
@login_required
def configure_honeypot(id):
    db_session = database_setup.get_session()
    honeypot = db_session.query(Honeypot).filter(Drone.id == id).one()
    if honeypot.discriminator != 'honeypot' or honeypot is None:
        abort(404, 'Drone with id {0} not found or invalid.'.format(id))
    config_dict = send_database_request('{0} {1}'.format(Messages.DRONE_CONFIG.value, id))
    config_obj = DictWrapper(config_dict)
    form = HoneypotConfigurationForm(obj=config_obj)
    if not form.validate_on_submit():
        return render_template('configure-honeypot.html', form=form, mode_name='Honeypot', user=current_user)
    else:
        honeypot.cert_common_name = form.certificate_info__common_name.data
        honeypot.cert_country = form.certificate_info__country.data
        honeypot.cert_state = form.certificate_info__state.data
        honeypot.cert_locality = form.certificate_info__locality.data
        honeypot.cert_organization = form.certificate_info__organization.data
        honeypot.cert_organization_unit = form.certificate_info__organization_unit.data

        # clear all capabilities
        honeypot.capabilities = []
        if form.capabilities__ftp__enabled.data:
            honeypot.add_capability('ftp', form.capabilities__ftp__port.data,
                                    {
                                        'max_attempts': form.capabilities__ftp__protocol_specific_data__max_attempts.data,
                                        'banner': form.capabilities__ftp__protocol_specific_data__banner.data,
                                        'syst_type': form.capabilities__ftp__protocol_specific_data__syst_type.data
                                    })

        if form.capabilities__telnet__enabled.data:
            honeypot.add_capability('telnet', form.capabilities__telnet__port.data,
                                    {
                                        'max_attempts': form.capabilities__telnet__protocol_specific_data__max_attempts.data,
                                    })

        if form.capabilities__pop3__enabled.data:
            honeypot.add_capability('pop3', form.capabilities__pop3__port.data,
                                    {
                                        'max_attempts': form.capabilities__pop3__protocol_specific_data__max_attempts.data,
                                    })

        if form.capabilities__pop3s__enabled.data:
            honeypot.add_capability('pop3s', form.capabilities__pop3s__port.data,
                                    {
                                        'max_attempts': form.capabilities__pop3s__protocol_specific_data__max_attempts.data,
                                    })

        if form.capabilities__ssh__enabled.data:
            honeypot.add_capability('ssh', form.capabilities__ssh__port.data, {})

        if form.capabilities__http__enabled.data:
            honeypot.add_capability('http', form.capabilities__http__port.data,
                                    {
                                        'banner': form.capabilities__http__protocol_specific_data__banner.data,
                                    })

        if form.capabilities__https__enabled.data:
            honeypot.add_capability('https', form.capabilities__https__port.data,
                                    {
                                        'banner': form.capabilities__https__protocol_specific_data__banner.data,
                                    })

        if form.capabilities__smtp__enabled.data:
            honeypot.add_capability('smtp', form.capabilities__smtp__port.data,
                                    {
                                        'banner': form.capabilities__smtp__protocol_specific_data__banner.data,
                                    })

        if form.capabilities__vnc__enabled.data:
            honeypot.add_capability('vnc', form.capabilities__vnc__port.data, {})

        honeypot.name = form.general__name.data
        db_session.add(honeypot)
        db_session.commit()

        send_database_request('{0} {1}'.format(Messages.DRONE_CONFIG_CHANGED.value, honeypot.id))
        return render_template('finish-config-honeypot.html', drone_id=honeypot.id, user=current_user)


@app.route('/ws/drone/client/configure/<id>', methods=['GET', 'POST'])
@login_required
def configure_client(id):
    db_session = database_setup.get_session()
    drone = db_session.query(Drone).filter(Drone.id == id).one()
    if drone.discriminator != 'client' or drone is None:
        abort(404, 'Drone with id {0} not found or invalid.'.format(id))
    config_dict = send_database_request('{0} {1}'.format(Messages.DRONE_CONFIG.value, id))
    config_obj = DictWrapper(config_dict)
    form = ClientConfigurationForm(obj=config_obj)
    if not form.validate_on_submit():
        return render_template('configure-client.html', form=form, mode_name='Client', user=current_user)
    else:
        bait_timing_config = {
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

        drone.bait_timings = json.dumps(bait_timing_config)
        db_session.add(drone)
        db_session.commit()

        send_database_request('{0} {1}'.format(Messages.DRONE_CONFIG_CHANGED.value, drone.id))
        return render_template('finish-config-client.html', drone_id=drone.id, user=current_user)



@app.route('/ws/drone/configure/<id>', methods=['GET', 'POST'])
@login_required
def configure_drone(id):
    db_session = database_setup.get_session()
    drone = db_session.query(Drone).filter(Drone.id == id).one()
    if drone is None:
        abort(404, 'Drone with id {0} could not be found.'.format(id))
    else:
        return render_template('drone_mode.html', drone_id=drone.id, user=current_user)


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
    drone_key = ''.join(random.SystemRandom().choice('0123456789abcdef') for i in range(6))
    drone_keys.append(drone_key)
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
        rsp = Response(response=bait_users, status=200, mimetype='application/json')
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
        send_database_request('{0} {1} {2}'.format(Messages.BAIT_USER_ADD.value, bait_user['username'], bait_user['password']))
    return ''


# deletes a single bait user or a list of users
@app.route('/ws/bait_users/delete', methods=['POST'])
@login_required
def delete_bait_user():
    # list of bait user id's
    bait_users = json.loads(request.data)
    for id in bait_users:
        send_database_request('{0} {1}'.format(Messages.BAIT_USER_DELETE.value, id))
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
    rsp = Response(response=sessions, status=200, mimetype='application/json')
    return rsp


@app.route('/data/session/<_id>/credentials')
@login_required
def data_session_credentials(_id):
    credentials = send_database_request('{0} {1}'.format(Messages.GET_SESSION_CREDENTIALS.value, _id))
    rsp = Response(response=credentials, status=200, mimetype='application/json')
    return rsp


@app.route('/data/session/<_id>/transcript')
@login_required
def data_session_transcript(_id):
    transcript = send_database_request('{0} {1}'.format(Messages.GET_SESSION_TRANSCRIPT.value, _id))
    rsp = Response(response=transcript, status=200, mimetype='application/json')
    return rsp


@app.route('/data/drones', defaults={'dronetype': None}, methods=['GET'])
@app.route('/data/drones/<dronetype>', methods=['GET'])
@login_required
def data_drones(dronetype):
    db_session = database_setup.get_session()
    if dronetype is None:
        drones = db_session.query(Drone).all()
    elif dronetype == 'unassigned':
        drones = db_session.query(Drone).filter(Drone.discriminator == None)
    else:
        drones = db_session.query(Drone).filter(Drone.discriminator == dronetype)

    rows = []
    for drone in drones:
        rows.append(drone.to_dict())
    rsp = Response(response=json.dumps(rows, indent=4), status=200, mimetype='application/json')
    return rsp


@app.route('/ws/drones', defaults={'dronetype': None})
@app.route('/ws/drones/<dronetype>')
@login_required
def drones(dronetype):
    return render_template('drones.html', user=current_user, dronetype=dronetype)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_session = database_setup.get_session()
        user = None
        try:
            user = db_session.query(User).filter(User.id == form.username.data).one()
        except NoResultFound:
            logger.info('Attempt to log in as non-existant user: {0}'.format(form.username.data))
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            logger.info('User {0} logged in.'.format(user.id))
            flash('Logged in successfully')
            return redirect(request.args.get("next") or '/')
    return render_template('login.html', form=form)


@app.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    flash('Logged out succesfully')
    return redirect('/login')

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
