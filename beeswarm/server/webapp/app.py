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
from sqlalchemy import desc
from werkzeug.security import check_password_hash
from wtforms import HiddenField
from flask import request

from beeswarm.server.webapp.auth import Authenticator
from forms import HoneypotConfigurationForm, ClientConfigurationForm, LoginForm, SettingsForm
from beeswarm.server.db import database_setup
from beeswarm.server.db.entities import Client, BaitSession, Session, Honeypot, User, BaitUser, Transcript, Drone, \
    Authentication
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

context = beeswarm.shared.zmq_context
config_actor_socket = context.socket(zmq.REQ)
config_actor_socket.connect(SocketNames.CONFIG_COMMANDS)
request_lock = gevent.lock.RLock()


def send_config_request(request):
    global config_actor_socket
    request_lock.acquire()
    try:
        return send_zmq_request_socket(config_actor_socket, request)
    finally:
        request_lock.release()

@login_manager.user_loader
def user_loader(userid):
    userid = userid.encode('utf-8')
    db_session = database_setup.get_session()
    user = None
    try:
        user = db_session.query(User).filter(User.id == userid).one()
    except NoResultFound:
        logger.info('Attempt to load non-existent user: {0}'.format(userid))
    return user


@app.route('/')
@login_required
def home():
    db_session = database_setup.get_session()
    status = {
        'nhoneypots': db_session.query(Honeypot).count(),
        'nclients': db_session.query(Client).count(),
        'nsessions': db_session.query(Session).count(),
        'nbees': db_session.query(BaitSession).count(),
        'nattacks': db_session.query(Session).filter(Session.classification_id != 'bait_session')\
                                             .filter(Session.classification_id is not None).count(),
        'attacks': {
            'http': get_num_attacks('http'),
            'vnc': get_num_attacks('vnc'),
            'ssh': get_num_attacks('ssh'),
            'ftp': get_num_attacks('ftp'),
            'https': get_num_attacks('https'),
            'pop3': get_num_attacks('pop3'),
            'pop3s': get_num_attacks('pop3s'),
            'smtp': get_num_attacks('smtp'),
            'telnet': get_num_attacks('telnet'),
        },
        'bees': {
            'successful': db_session.query(BaitSession).filter(BaitSession.did_login).count(),
            'failed': db_session.query(BaitSession).filter(not BaitSession.did_login).count(),

        }
    }
    urls = {
        'honeypotdata': '/data/honeypots',
        'clientdata': '/data/clients',
        'delhoneypot': '/ws/honeypot/delete',
        'delclient': '/ws/client/delete'
    }
    return render_template('index.html', user=current_user, status=status, urls=urls)


def get_num_attacks(protocol):
    db_session = database_setup.get_session()
    return db_session.query(Session).filter(Session.classification_id != 'bait_session')\
                                    .filter(Session.classification_id is not None)\
                                    .filter(Session.protocol == protocol).count()

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
    config_dict = send_config_request('{0} {1}'.format(Messages.DRONE_CONFIG, id))
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
        # advise config actor that we have change something on a given drone id
        # TODO: make entity itself know if it has changed and then poke the config actor.

        send_config_request('{0} {1}'.format(Messages.DRONE_CONFIG_CHANGED, honeypot.id))
        return render_template('finish-config-honeypot.html', drone_id=honeypot.id, user=current_user)


@app.route('/ws/drone/client/configure/<id>', methods=['GET', 'POST'])
@login_required
def configure_client(id):
    db_session = database_setup.get_session()
    drone = db_session.query(Drone).filter(Drone.id == id).one()
    if drone.discriminator != 'client' or drone is None:
        abort(404, 'Drone with id {0} not found or invalid.'.format(id))
    config_dict = send_config_request('{0} {1}'.format(Messages.DRONE_CONFIG, id))
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

        send_config_request('{0} {1}'.format(Messages.DRONE_CONFIG_CHANGED, drone.id))
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

    server_host = send_config_request('{0} {1}'.format(Messages.GET_CONFIG_ITEM, 'network,server_host'))
    server_web_port = send_config_request('{0} {1}'.format(Messages.GET_CONFIG_ITEM, 'network,web_port'))
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
        config_json = send_config_request('{0}'.format(Messages.DRONE_ADD))
        return json.dumps(config_json)


@app.route('/ws/drone/delete', methods=['POST'])
@login_required
def delete_drones():
    # list of drone id's'
    drone_ids = json.loads(request.data)
    for drone_id in drone_ids:
        send_config_request('{0} {1}'.format(Messages.DRONE_DELETE, drone_id))
    return ''

# requesting all bait users - or replacing all bait users
@app.route('/ws/bait_users', methods=['GET', 'POST'])
@login_required
def get_bait_users():
    db_session = database_setup.get_session()
    if request.method == 'GET':
        bait_users = db_session.query(BaitUser)
        rows = []
        for bait_user in bait_users:
            row = {'id': bait_user.id, 'username': bait_user.username, 'password': bait_user.password}
            rows.append(row)
        rsp = Response(response=json.dumps(rows, indent=4), status=200, mimetype='application/json')
        return rsp
    else:
        db_session.query(BaitUser).delete()
        bait_users = json.loads(request.data)
        for bait_user in bait_users:
            new_bait_users = BaitUser(username=bait_user['username'], password=bait_user['password'])
            db_session.add(new_bait_users)
    db_session.commit()
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
        send_config_request('{0} {1} {2}'.format(Messages.BAIT_USER_ADD, bait_user['username'], bait_user['password']))
    return ''


# deletes a single bait user or a list of users
@app.route('/ws/bait_users/delete', methods=['POST'])
@login_required
def delete_bait_user():
    # list of bait user id's
    bait_users = json.loads(request.data)
    for id in bait_users:
        send_config_request('{0} {1}'.format(Messages.BAIT_USER_DELETE, id))
    return ''


@app.route('/data/sessions/<_type>', methods=['GET'])
@login_required
def data_sessions_attacks(_type):
    db_session = database_setup.get_session()
    # the database_setup will not get hit until we start iterating the query object
    query_iterators = {
        'all': db_session.query(Session),
        'bait_sessions': db_session.query(BaitSession),
        'attacks': db_session.query(Session).filter(Session.classification_id != 'bait_session')
    }

    if _type not in query_iterators:
        return 'Not Found', 404

    # select which iterator to use
    entries = query_iterators[_type].order_by(desc(Session.timestamp))

    rows = []
    for session in entries:
        rows.append(session.to_dict())
    rsp = Response(response=json.dumps(rows, indent=4), status=200, mimetype='application/json')
    return rsp


@app.route('/data/session/<_id>/credentials')
@login_required
def data_session_credentials(_id):
    db_session = database_setup.get_session()

    credentials = db_session.query(Authentication).filter(Authentication.session_id == _id)
    return_rows = []
    for c in credentials:
        return_rows.append(c.to_dict())
    rsp = Response(response=json.dumps(return_rows, indent=4), status=200, mimetype='application/json')
    return rsp


@app.route('/data/session/<_id>/transcript')
@login_required
def data_session_transcript(_id):
    db_session = database_setup.get_session()

    transcripts = db_session.query(Transcript).filter(Transcript.session_id == _id)
    return_rows = []
    for t in transcripts:
        row = {'time': t.timestamp.strftime('%Y-%m-%d %H:%M:%S'), 'direction': t.direction, 'data': t.data}
        return_rows.append(row)
    rsp = Response(response=json.dumps(return_rows, indent=4), status=200, mimetype='application/json')
    return rsp


@app.route('/data/honeypots', methods=['GET'])
@login_required
def data_honeypots():
    db_session = database_setup.get_session()
    honeypots = db_session.query(Honeypot).all()
    rows = []
    for h in honeypots:
        row = {'honeypot_id': h.id, 'attacks': db_session.query(Session).filter(Session.honeypot_id == h.id).count(),
               'checked': False, 'name': h.name}
        rows.append(row)
    rsp = Response(response=json.dumps(rows, indent=4), status=200, mimetype='application/json')
    return rsp


@app.route('/data/clients', methods=['GET'])
@login_required
def data_clients():
    db_session = database_setup.get_session()
    clients = db_session.query(Client).all()
    rows = []
    for client in clients:
        row = {'client_id': client.id,
               'bees': db_session.query(BaitSession).filter(BaitSession.client_id == client.id).count(),
               'checked': False, 'name': client.name}
        rows.append(row)
    rsp = Response(response=json.dumps(rows, indent=4), status=200, mimetype='application/json')
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
        print drone.to_dict()
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
    bait_session_retain = send_config_request('{0} {1}'.format(Messages.GET_CONFIG_ITEM, 'bait_session_retain'))
    ignore_failed_bait_session = ast.literal_eval(send_config_request('{0} {1}'.format(Messages.GET_CONFIG_ITEM, 'ignore_failed_bait_session')))
    malicious_session_retain = send_config_request('{0} {1}'.format(Messages.GET_CONFIG_ITEM, 'malicious_session_retain'))
    form = SettingsForm(bait_session_retain=bait_session_retain, malicious_session_retain=malicious_session_retain,
                        ignore_failed_bait_session=ignore_failed_bait_session)

    if form.validate_on_submit():
        # the potential updates that we want to save to config file.
        options = {'bait_session_retain': form.bait_session_retain.data,
                   'malicious_session_retain': form.malicious_session_retain.data,
                   'ignore_failed_bait_session': form.ignore_failed_bait_session.data}
        send_config_request('{0} {1}'.format(Messages.SET_CONFIG_ITEM, json.dumps(options)))
    return render_template('settings.html', form=form, user=current_user)


if __name__ == '__main__':
    app.run()
