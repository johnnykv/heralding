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
import os
import random
import shutil
import string
import tempfile
import uuid
from collections import namedtuple

import gevent
import zmq.green as zmq
from flask import Flask, render_template, request, redirect, flash, Response, send_from_directory, abort
from flask.ext.login import LoginManager, login_user, current_user, login_required, logout_user
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import desc
from werkzeug.security import check_password_hash
from wtforms import HiddenField

from beeswarm.server.webapp.auth import Authenticator
import beeswarm
from forms import HoneypotConfigurationForm, NewClientConfigForm, LoginForm, SettingsForm
from beeswarm.server.db import database_setup
from beeswarm.server.db.entities import Client, BaitSession, Session, Honeypot, User, BaitUser, Transcript, Drone, \
    Authentication
from beeswarm.shared.helpers import send_zmq_request
from beeswarm.shared.message_enum import Messages


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

config = {}

logger = logging.getLogger(__name__)

authenticator = Authenticator()
first_cfg_received = gevent.event.Event()

# keys used for adding new drones to the system
drone_keys = []


@app.before_first_request
def initialize():
    gevent.spawn(config_subscriber)
    # wait until we have received the first config publish
    first_cfg_received.wait()


def config_subscriber():
    global config
    ctx = zmq.Context()
    subscriber_socket = ctx.socket(zmq.SUB)
    subscriber_socket.connect('ipc://configPublisher')
    subscriber_socket.setsockopt(zmq.SUBSCRIBE, Messages.CONFIG_FULL)
    send_zmq_request('ipc://configCommands', Messages.PUBLISH_CONFIG)
    while True:
        poller = zmq.Poller()
        poller.register(subscriber_socket, zmq.POLLIN)
        while True:
            socks = dict(poller.poll(100))
            if subscriber_socket in socks and socks[subscriber_socket] == zmq.POLLIN:
                topic, msg = subscriber_socket.recv().split(' ', 1)
                config = json.loads(msg)
                first_cfg_received.set()
                logger.debug('Config received')


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
        'nattacks': db_session.query(Session).filter(Session.classification_id != 'bait_session' and
                                                     Session.classification_id is not None).count(),
        'attacks': {
            'http': db_session.query(Session).filter(Session.classification_id != 'bait_session' and
                                                     Session.classification_id is not None and
                                                     Session.protocol == 'http').count(),
            'vnc': db_session.query(Session).filter(Session.classification_id != 'bait_session' and
                                                    Session.classification_id is not None and
                                                    Session.protocol == 'vnc').count(),
            'ssh': db_session.query(Session).filter(Session.classification_id != 'bait_session' and
                                                    Session.classification_id is not None and
                                                    Session.protocol == 'ssh').count(),
            'ftp': db_session.query(Session).filter(Session.classification_id != 'bait_session' and
                                                    Session.classification_id is not None and
                                                    Session.protocol == 'ftp').count(),
            'https': db_session.query(Session).filter(Session.classification_id != 'bait_session' and
                                                      Session.classification_id is not None and
                                                      Session.protocol == 'https').count(),
            'pop3': db_session.query(Session).filter(Session.classification_id != 'bait_session' and
                                                     Session.classification_id is not None and
                                                     Session.protocol == 'pop3').count(),
            'pop3s': db_session.query(Session).filter(Session.classification_id != 'bait_session' and
                                                      Session.classification_id is not None and
                                                      Session.protocol == 'pop3s').count(),
            'smtp': db_session.query(Session).filter(Session.classification_id != 'bait_session' and
                                                     Session.classification_id is not None and
                                                     Session.protocol == 'smtp').count(),
            'telnet': db_session.query(Session).filter(Session.classification_id != 'bait_session' and
                                                       Session.classification_id is not None and
                                                       Session.protocol == 'telnet').count(),
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
    config_dict = send_zmq_request('ipc://configCommands', '{0} {1}'.format(Messages.DRONE_CONFIG, id))
    config_obj = DictWrapper(config_dict)
    # if honeypot.configuration is not None:
    # config_obj = DictWrapper(json.loads(honeypot.configuration))
    # else:
    # # virgin drone
    # config_obj = None
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
                                        'banner': form.capabilities__http__protocol_specific_data__banner,
                                    })

        if form.capabilities__https__enabled.data:
            honeypot.add_capability('https', form.capabilities__https__port.data,
                                    {
                                        'banner': form.capabilities__https__protocol_specific_data__banner,
                                    })

        if form.capabilities__smtp__enabled.data:
            honeypot.add_capability('smtp', form.capabilities__smtp__port.data,
                                    {
                                        'banner': form.capabilities__smtp__protocol_specific_data__banner,
                                    })

        if form.capabilities__vnc__enabled.data:
            honeypot.add_capability('vnc', form.capabilities__vnc__port.data, {})

        honeypot.name = form.general__name.data
        db_session.add(honeypot)
        db_session.commit()
        # advise config actor that we have change something on a given drone id
        # TODO: make entity itself know if it has changed and then poke the config actor.

        send_zmq_request('ipc://configCommands', '{0} {1}'.format(Messages.DRONE_CONFIG_CHANGED, honeypot.id))
        return render_template('finish-config-honeypot.html', drone_id=honeypot.id, user=current_user)


@app.route('/ws/drone/client/configure/<id>', methods=['GET', 'POST'])
@login_required
def configure_client(id):
    db_session = database_setup.get_session()
    drone = db_session.query(Drone).filter(Drone.id == id).one()
    if drone.discriminator != 'client' or drone is None:
        abort(404, 'Drone with id {0} not found or invalid.'.format(id))
    send_zmq_request('ipc://configCommands', '{0} {1}'.format(Messages.DRONE_CONFIG_CHANGED, drone.id))
    return render_template('finish-config-client.html', drone_id=drone.id, user=current_user)


@app.route('/ws/drone/configure/<id>', methods=['GET', 'POST'])
@login_required
def configure_drone(id):
    print id
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

    server_https = 'https://{0}:{1}/'.format(config['network']['server_host'], config['network']['web_port'])
    drone_link = '{0}ws/drone/add/{1}'.format(server_https, drone_key)
    iso_link = '/NotWorkingYet'
    return render_template('add_drone.html', user=current_user, drone_link=drone_link,
                           iso_link=iso_link)


# TODO: throttle this
@app.route('/ws/drone/add/<key>', methods=['GET'])
def drone_key(key):
    global drone_keys
    if key not in drone_keys:
        logger.warn('Attempt to add new drone, but using wrong key from: {0}'.format(request.remote_addr))
        abort(401)
    else:
        drone_id = str(uuid.uuid4())
        db_session = database_setup.get_session()
        drone = Drone(id=drone_id)
        db_session.add(drone)
        db_session.commit()
        config_json = send_zmq_request('ipc://configCommands', '{0} {1}'.format(Messages.DRONE_CONFIG, drone_id))
        return json.dumps(config_json)


@app.route('/ws/drone/delete', methods=['POST'])
@login_required
def delete_drones():
    # list of drone id's'
    drone_ids = json.loads(request.data)
    for drone_id in drone_ids:
        send_zmq_request('ipc://configCommands', '{0} {1}'.format(Messages.DRONE_DELETE, drone_id))
    return ''


@app.route('/ws/client', methods=['GET', 'POST'])
@login_required
def create_client():
    form = NewClientConfigForm()
    client_id = str(uuid.uuid4())
    if form.validate_on_submit():
        server_zmq_url = 'tcp://{0}:{1}'.format(config['network']['server_host'], config['network']['zmq_port'])
        result = send_zmq_request('ipc://configCommands', '{0} {1}'.format(Messages.GEN_ZMQ_KEYS, client_id))
        zmq_public = result['public_key']
        zmq_private = result['private_key']

        client_config = {
            'general': {
                'mode': 'client',
                'id': client_id,
                'fetch_ip': False
            },
            'bait_sessions': {
                'http': {
                    'enabled': form.http_enabled.data,
                    'server': form.http_server.data,
                    'port': form.http_port.data,
                    'timing': {
                        'active_range': form.http_active_range.data,
                        'sleep_interval': form.http_sleep_interval.data,
                        'activation_probability': form.http_activation_probability.data
                    },
                    'username': form.http_login.data,
                    'password': form.http_password.data
                },
                'ftp': {
                    'enabled': form.ftp_enabled.data,
                    'server': form.ftp_server.data,
                    'port': form.ftp_port.data,
                    'timing': {
                        'active_range': form.ftp_active_range.data,
                        'sleep_interval': form.ftp_sleep_interval.data,
                        'activation_probability': form.ftp_activation_probability.data
                    },
                    'username': form.ftp_login.data,
                    'password': form.ftp_password.data
                },
                'https': {
                    'enabled': form.https_enabled.data,
                    'server': form.https_server.data,
                    'port': form.https_port.data,
                    'timing': {
                        'active_range': form.https_active_range.data,
                        'sleep_interval': form.https_sleep_interval.data,
                        'activation_probability': form.https_activation_probability.data
                    },
                    'username': form.https_login.data,
                    'password': form.https_password.data
                },
                'pop3': {
                    'enabled': form.pop3_enabled.data,
                    'server': form.pop3_server.data,
                    'port': form.pop3_port.data,
                    'timing': {
                        'active_range': form.pop3_active_range.data,
                        'sleep_interval': form.pop3_sleep_interval.data,
                        'activation_probability': form.pop3_activation_probability.data
                    },
                    'username': form.pop3_login.data,
                    'password': form.pop3_password.data
                },
                'ssh': {
                    'enabled': form.ssh_enabled.data,
                    'server': form.ssh_server.data,
                    'port': form.ssh_port.data,
                    'timing': {
                        'active_range': form.ssh_active_range.data,
                        'sleep_interval': form.ssh_sleep_interval.data,
                        'activation_probability': form.ssh_activation_probability.data
                    },
                    'username': form.ssh_login.data,
                    'password': form.ssh_password.data
                },
                'pop3s': {
                    'enabled': form.pop3s_enabled.data,
                    'server': form.pop3s_server.data,
                    'port': form.pop3s_port.data,
                    'timing': {
                        'active_range': form.pop3s_active_range.data,
                        'sleep_interval': form.pop3s_sleep_interval.data,
                        'activation_probability': form.pop3s_activation_probability.data
                    },
                    'username': form.pop3s_login.data,
                    'password': form.pop3s_password.data
                },
                'smtp': {
                    'enabled': form.smtp_enabled.data,
                    'server': form.smtp_server.data,
                    'port': form.smtp_port.data,
                    'timing': {
                        'active_range': form.smtp_active_range.data,
                        'sleep_interval': form.smtp_sleep_interval.data,
                        'activation_probability': form.smtp_activation_probability.data
                    },
                    'username': form.smtp_login.data,
                    'local_hostname': form.smtp_local_hostname.data,
                    'password': form.smtp_password.data
                },
                'vnc': {
                    'enabled': form.vnc_enabled.data,
                    'server': form.vnc_server.data,
                    'port': form.vnc_port.data,
                    'timing': {
                        'active_range': form.vnc_active_range.data,
                        'sleep_interval': form.vnc_sleep_interval.data,
                        'activation_probability': form.vnc_activation_probability.data
                    },
                    'username': form.vnc_login.data,
                    'password': form.vnc_password.data
                },
                'telnet': {
                    'enabled': form.telnet_enabled.data,
                    'server': form.telnet_server.data,
                    'port': form.telnet_port.data,
                    'timing': {
                        'active_range': form.telnet_active_range.data,
                        'sleep_interval': form.telnet_sleep_interval.data,
                        'activation_probability': form.telnet_activation_probability.data
                    },
                    'username': form.telnet_login.data,
                    'password': form.telnet_password.data
                }
            },
            'beeswarm_server': {
                'enabled': True,
                'zmq_url': server_zmq_url,
                'zmq_server_public': config['network']['zmq_server_public_key'],
                'zmq_own_public': zmq_public,
                'zmq_own_private': zmq_private,
            },
        }
        config_json = json.dumps(client_config, indent=4)

        db_session = database_setup.get_session()
        f = Client(id=client_id, configuration=config_json)
        db_session.add(f)
        db_session.commit()
        return render_template('finish-config-client.html', user=current_user)


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
    db_session = database_setup.get_session()
    bait_users = json.loads(request.data)
    for bait_user in bait_users:
        # TODO: Also validate client side
        if bait_user['username'] == '':
            continue
        existing_bait_user = db_session.query(BaitUser).filter(BaitUser.username == bait_user['username'],
                                                               BaitUser.password == bait_user['password'])
        if not existing_bait_user:
            new_bait_user = BaitUser(username=bait_user['username'], password=bait_user['password'])
            db_session.add(new_bait_user)
    db_session.commit()
    return ''


# deletes a single bait user or a list of users
@app.route('/ws/bait_users/delete', methods=['POST'])
@login_required
def delete_bait_user():
    db_session = database_setup.get_session()
    # list of bait user id's
    bait_users = json.loads(request.data)
    for id in bait_users:
        bait_user_to_delete = db_session.query(BaitUser).filter(BaitUser.id == int(id)).one()
        db_session.delete(bait_user_to_delete)
        send_zmq_request('ipc://configCommands', '{0} {1} {2} {3}'.format(Messages.BAIT_USER_DELETED,
                                                                          bait_user_to_delete.id,
                                                                          bait_user_to_delete.username,
                                                                          bait_user_to_delete.password))
    db_session.commit()
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
    for a in entries:
        auth_attempts = []
        for attempt in a.authentication:
            auth_attempts.append(
                {'username': attempt.username,
                 'password': attempt.password,
                 'successful': attempt.successful})
        classification = a.classification_id.replace('_', ' ').capitalize()
        row = {'time': a.timestamp.strftime('%Y-%m-%d %H:%M:%S'), 'protocol': a.protocol, 'ip_address': a.source_ip,
               'classification': classification, 'id': a.id, 'auth_attempts': auth_attempts}
        rows.append(row)
    rsp = Response(response=json.dumps(rows, indent=4), status=200, mimetype='application/json')
    return rsp


@app.route('/data/session/<_id>/credentials')
@login_required
def data_session_credentials(_id):
    db_session = database_setup.get_session()

    credentials = db_session.query(Authentication).filter(Authentication.session_id == _id)
    return_rows = []
    for c in credentials:
        return_rows.append({'username': c.username,
                            'password': c.password,
                            'successful': c.successful})
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
    for d in drones:
        if d.last_activity == datetime.min:
            timestamp = 'Never'
        else:
            timestamp = d.last_activity.strftime('%Y-%m-%d %H:%M:%S')
        if d.discriminator is None:
            _type = ''
        else:
            _type = d.discriminator.capitalize()
        row = {'id': d.id, 'name': d.name, 'type': _type, 'last_activity': timestamp}
        rows.append(row)
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


@app.route('/iso/honeypot/<honeypot_id>.iso', methods=['GET'])
@login_required
def generate_honeypot_iso(honeypot_id):
    logger.info('Generating new ISO for Honeypot ({})'.format(honeypot_id))
    db_session = database_setup.get_session()
    current_honeypot = db_session.query(Honeypot).filter(Honeypot.id == honeypot_id).one()

    tempdir = tempfile.mkdtemp()
    custom_config_dir = os.path.join(tempdir, 'custom_config')
    os.makedirs(custom_config_dir)

    package_directory = os.path.dirname(os.path.abspath(beeswarm.__file__))
    logger.debug('Copying data files to temporary directory.')
    shutil.copytree(os.path.join(package_directory, 'honeypot/data'), os.path.join(custom_config_dir, 'data/'))

    config_file_path = os.path.join(custom_config_dir, 'beeswarmcfg.json')
    with open(config_file_path, 'w') as config_file:
        config_file.write(current_honeypot.configuration)

    if not write_to_iso(tempdir, current_honeypot):
        return 'Not Found', 404
    temp_iso_name = 'beeswarm-{}-{}.iso'.format(current_honeypot.__class__.__name__,
                                                current_honeypot.id)

    return send_from_directory(tempdir, temp_iso_name, mimetype='application/iso-image')


@app.route('/iso/client/<client_id>.iso', methods=['GET'])
@login_required
def generate_client_iso(client_id):
    logger.info('Generating new ISO for Client ({})'.format(client_id))
    db_session = database_setup.get_session()
    client = db_session.query(Client).filter(Client.id == client_id).one()

    tempdir = tempfile.mkdtemp()
    custom_config_dir = os.path.join(tempdir, 'custom_config')
    os.makedirs(custom_config_dir)

    config_file_path = os.path.join(custom_config_dir, 'beeswarmcfg.json')
    with open(config_file_path, 'w') as config_file:
        config_file.write(client.configuration)

    if not write_to_iso(tempdir, client):
        return 'Not Found', 404
    temp_iso_name = 'beeswarm-{}-{}.iso'.format(client.__class__.__name__,
                                                client.id)
    return send_from_directory(tempdir, temp_iso_name, mimetype='application/iso-image')


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    global config
    # we need getattr for WTF
    formdata = namedtuple('Struct', config.keys())(*config.values())
    form = SettingsForm(obj=formdata, bait_session_retain=config['bait_session_retain'])

    if form.validate_on_submit():
        # the potential updates that we want to save to config file.
        options = {'bait_session_retain': form.bait_session_retain.data,
                   'malicious_session_retain': form.malicious_session_retain.data,
                   'ignore_failed_bait_session': form.ignore_failed_bait_session.data}
        update_config(options)
    return render_template('settings.html', form=form, user=current_user)


def update_config(options):
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect('ipc://configCommands')
    socket.send('{0} {1}'.format(Messages.SET, json.dumps(options)))
    reply = socket.recv()
    if reply != Messages.OK:
        logger.warning('Error while requesting config change to actor.')
    socket.close()


def write_to_iso(temporary_dir, mode):
    iso_file_path = config['iso']['path']

    if config['iso']['offset'] == -1:
        logger.warning('Invalid offset in config file.')
        return False

    custom_config_dir = os.path.join(temporary_dir, 'custom_config')

    try:
        # Change directory to create the tar archive in the temp directory
        save_cwd = os.getcwd()
        os.chdir(temporary_dir)
        config_archive = shutil.make_archive(str(mode.id), 'gztar', custom_config_dir, verbose=True)
    finally:
        os.chdir(save_cwd)

    temp_iso_name = 'beeswarm-{}-{}.iso'.format(mode.__class__.__name__, mode.id)
    temp_iso_path = os.path.join(temporary_dir, temp_iso_name)
    try:
        shutil.copyfile(iso_file_path, temp_iso_path)
    except IOError:
        logger.warning('Couldn\'t find the ISO specified in the config: {}'.format(iso_file_path))
        return False

    with open(temp_iso_path, 'r+b') as isofile:
        isofile.seek(config['iso']['offset'])
        with open(config_archive, 'rb') as tarfile:
            isofile.write(tarfile.read())
    return True


if __name__ == '__main__':
    app.run()
