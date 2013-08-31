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
from flask import Flask, render_template, request, redirect, flash, Response, send_from_directory
from flask.ext.login import LoginManager, login_user, current_user, login_required, logout_user
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.security import check_password_hash
from wtforms import HiddenField
import beeswarm
from forms import NewHiveConfigForm, NewFeederConfigForm, LoginForm, SettingsForm
from beeswarm.beekeeper.db import database
from beeswarm.beekeeper.db.entities import Feeder, Honeybee, Session, Hive, User, SessionData, Authentication


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


@login_manager.user_loader
def user_loader(userid):
    userid = userid.encode('utf-8')
    db_session = database.get_session()
    user = None
    try:
        user = db_session.query(User).filter(User.id == userid).one()
    except NoResultFound:
        logging.info('Attempt to load non-existent user: {0}'.format(userid))
    return user


logger = logging.getLogger(__name__)


@app.route('/')
@login_required
def home():
    db_session = database.get_session()
    status = {
        'nhives': db_session.query(Hive).count(),
        'nfeeders': db_session.query(Feeder).count(),
        'nsessions': db_session.query(Session).count(),
        'nbees': db_session.query(Honeybee).count(),
        'nattacks': db_session.query(Session).filter(Session.classification_id != 'honeybee' and
                                                     Session.classification_id is not None).count(),
        'attacks': {
            'http': db_session.query(Session).filter(Session.classification_id != 'honeybee' and
                                                     Session.classification_id is not None and
                                                     Session.protocol == 'http').count(),
            'vnc': db_session.query(Session).filter(Session.classification_id != 'honeybee' and
                                                    Session.classification_id is not None and
                                                    Session.protocol == 'vnc').count(),
            'ssh': db_session.query(Session).filter(Session.classification_id != 'honeybee' and
                                                    Session.classification_id is not None and
                                                    Session.protocol == 'ssh').count(),
            'ftp': db_session.query(Session).filter(Session.classification_id != 'honeybee' and
                                                    Session.classification_id is not None and
                                                    Session.protocol == 'ftp').count(),
            'https': db_session.query(Session).filter(Session.classification_id != 'honeybee' and
                                                      Session.classification_id is not None and
                                                      Session.protocol == 'https').count(),
            'pop3': db_session.query(Session).filter(Session.classification_id != 'honeybee' and
                                                     Session.classification_id is not None and
                                                     Session.protocol == 'pop3').count(),
            'pop3s': db_session.query(Session).filter(Session.classification_id != 'honeybee' and
                                                      Session.classification_id is not None and
                                                      Session.protocol == 'pop3s').count(),
            'smtp': db_session.query(Session).filter(Session.classification_id != 'honeybee' and
                                                     Session.classification_id is not None and
                                                     Session.protocol == 'smtp').count(),
            'telnet': db_session.query(Session).filter(Session.classification_id != 'honeybee' and
                                                       Session.classification_id is not None and
                                                       Session.protocol == 'telnet').count(),
        },
        'bees': {
            'successful': db_session.query(Honeybee).filter(Honeybee.did_login).count(),
            'failed': db_session.query(Honeybee).filter(not Honeybee.did_login).count(),

        }
    }
    urls = {
        'hivedata': '/data/hives',
        'feederdata': '/data/feeders',
        'delhive': '/ws/hive/delete',
        'delfeeder': '/ws/feeder/delete'
    }
    return render_template('index.html', user=current_user, status=status, urls=urls)


@app.route('/sessions')
@login_required
def sessions_all():
    return render_template('logs.html', logtype='All', user=current_user)


@app.route('/sessions/honeybees')
@login_required
def sessions_honeybees():
    return render_template('logs.html', logtype='HoneyBees', user=current_user)


@app.route('/sessions/attacks')
@login_required
def sessions_attacks():
    return render_template('logs.html', logtype='Attacks', user=current_user)


@app.route('/ws/feeder_data', methods=['POST'])
@login_required
def feeder_data():
    #TODO: investigate why the flask provided request.json returns None
    data = json.loads(request.data)
    logger.debug(data)
    session = database.get_session()

    _feeder = session.query(Feeder).filter(Feeder.id == data['feeder_id']).one()

    if data['hive_id'] is not None:
        _hive = session.query(Hive).filter(Hive.id == data['hive_id']).one()
    else:
        _hive = None

    h = Honeybee(
        id=data['id'],
        timestamp=datetime.strptime(data['timestamp'], '%Y-%m-%dT%H:%M:%S.%f'),
        received=datetime.utcnow(),
        protocol=data['protocol'],
        destination_ip=data['destination_ip'],
        destination_port=data['destination_port'],
        source_ip=data['source_ip'],
        source_port=data['source_port'],
        did_connect=data['did_connect'],
        did_login=data['did_login'],
        did_complete=data['did_complete'],
        feeder=_feeder,
        hive=_hive
    )

    for auth in data['authentication']:
        a = Authentication(id=auth['id'], username=auth['username'], password=auth['password'],
                           successful=auth['successful'],
                           timestamp=datetime.strptime(auth['timestamp'], '%Y-%m-%dT%H:%M:%S.%f'))
        h.authentication.append(a)

    session.add(h)
    session.commit()
    return ''


@app.route('/ws/hive_data', methods=['POST'])
@login_required
def hive_data():
    #TODO: investigate why the flask provided request.json returns None.
    data = json.loads(request.data)
    logger.debug('Received: {0}'.format(data))

    db_session = database.get_session()
    _hive = db_session.query(Hive).filter(Hive.id == data['hive_id']).one()

    session = Session(
        id=data['id'],
        timestamp=datetime.strptime(data['timestamp'], '%Y-%m-%dT%H:%M:%S.%f'),
        received=datetime.utcnow(),
        protocol=data['protocol'],
        destination_ip=data['destination_ip'],
        destination_port=data['destination_port'],
        source_ip=data['source_ip'],
        source_port=data['source_port'],
        hive=_hive)

    for auth in data['authentication']:
        a = Authentication(id=auth['id'], username=auth['username'], password=auth['password'],
                           successful=auth['successful'],
                           timestamp=datetime.strptime(auth['timestamp'], '%Y-%m-%dT%H:%M:%S.%f'))
        session.authentication.append(a)

    db_session.add(session)
    db_session.commit()

    return ''


@app.route('/ws/hive/config/<hive_id>', methods=['GET'])
def get_hive_config(hive_id):
    db_session = database.get_session()
    current_hive = db_session.query(Hive).filter(Hive.id == hive_id).one()
    return current_hive.configuration


@app.route('/ws/feeder/config/<feeder_id>', methods=['GET'])
def get_feeder_config(feeder_id):
    db_session = database.get_session()
    current_feeder = db_session.query(Feeder).filter(Feeder.id == feeder_id).one()
    return current_feeder.configuration


@app.route('/ws/hive', methods=['GET', 'POST'])
@login_required
def create_hive():
    form = NewHiveConfigForm()
    new_hive_id = str(uuid.uuid4())
    if form.validate_on_submit():
        with open(app.config['CERT_PATH']) as cert:
            cert_str = cert.read()
        beekeeper_password = str(uuid.uuid4())
        config = {
            'general': {
                'hive_id': new_hive_id,
                'hive_ip': '192.168.1.1',
                'fetch_ip': False
            },
            'log_hpfeedslogger': {
                'enabled': False,
                'host': 'hpfriends.honeycloud.net',
                'port': 20000,
                'ident': '2wtadBoH',
                'secret': 'mJPyhNhJmLYGbDCt',
                'chan': 'beeswarm.hive',
                'port_mapping': '{}'
            },
            'log_beekeeper': {
                'enabled': False,
                'beekeeper_url': 'https://127.0.0.1:5000/',
                'beekeeper_pass': beekeeper_password,
                'cert': cert_str
            },
            'log_syslog': {
                'enabled': False,
                'socket': '/dev/log'
            },
            "cap_ftp": {
                "enabled": form.ftp_enabled.data,
                "port": form.ftp_port.data,
                "max_attempts": form.ftp_max_attempts.data,
                "banner": form.ftp_banner.data,
                "syst_type": form.ftp_syst_type.data
            },
            "cap_telnet": {
                "enabled": form.telnet_enabled.data,
                "port": form.telnet_port.data,
                "max_attempts": form.telnet_max_attempts.data
            },
            "cap_pop3": {
                "enabled": form.pop3_enabled.data,
                "port": form.pop3_port.data,
                "max_attempts": form.pop3_max_attempts.data
            },
            "cap_pop3s": {
                "enabled": form.pop3s_enabled.data,
                "port": form.pop3s_port.data,
                "max_attempts": form.pop3s_max_attempts.data
            },
            "cap_ssh": {
                "enabled": form.ssh_enabled.data,
                "port": form.ssh_port.data,
                "key": form.ssh_key.data
            },
            "cap_http": {
                "enabled": form.http_enabled.data,
                "port": form.http_port.data,
                "banner": form.http_banner.data
            },
            "cap_https": {
                "enabled": form.https_enabled.data,
                "port": form.https_port.data,
                "banner": form.https_banner.data
            },
            "cap_smtp": {
                "enabled": form.smtp_enabled.data,
                "port": form.smtp_port.data,
                "banner": form.smtp_banner.data
            },
            "cap_vnc": {
                "enabled": form.vnc_enabled.data,
                "port": form.vnc_port.data
            },
            "timecheck": {
                "enabled": True,
                "poll": 5,
                "ntp_pool": "pool.ntp.org"
            },
        }
        config_json = json.dumps(config)

        db_session = database.get_session()
        h = Hive(id=new_hive_id, configuration=config_json)
        u = User(id=new_hive_id, nickname='Hive', password=beekeeper_password, utype=1)
        db_session.add_all([h, u])
        db_session.commit()
        config_link = '/ws/hive/config/{0}'.format(new_hive_id)
        iso_link = '/iso/hive/{0}.iso'.format(new_hive_id)
        return render_template('finish-config.html', mode_name='Hive', user=current_user,
                               config_link=config_link, iso_link=iso_link)

    return render_template('create-config.html', form=form, mode_name='Hive', user=current_user)


@app.route('/ws/hive/delete', methods=['POST'])
@login_required
def delete_hives():
    hive_ids = json.loads(request.data)
    db_session = database.get_session()
    for hive in hive_ids:
        hive_id = hive['hive_id']
        to_delete = db_session.query(Hive).filter(Hive.id == hive_id).one()
        huser = db_session.query(User).filter(User.id == hive_id).one()
        bees = db_session.query(Honeybee).filter(Honeybee.hive_id == hive_id)
        for s in to_delete.sessions:
            db_session.delete(s)
        for b in bees:
            db_session.delete(b)
        db_session.delete(to_delete)
        db_session.delete(huser)
    db_session.commit()
    return ''


@app.route('/ws/feeder', methods=['GET', 'POST'])
@login_required
def create_feeder():
    form = NewFeederConfigForm()
    new_feeder_id = str(uuid.uuid4())
    if form.validate_on_submit():
        with open(app.config['CERT_PATH']) as cert:
            cert_str = cert.read()
        beekeeper_password = str(uuid.uuid4())
        config = {
            'general': {
                'feeder_id': new_feeder_id,
                'hive_id': None
            },
            'public_ip': {
                'fetch_ip': True
            },
            'bee_http': {
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
            'bee_ftp': {
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
            'bee_pop3': {
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
            'bee_ssh': {
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
            'bee_pop3s': {
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
            'bee_smtp': {
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
            'bee_vnc': {
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
            'bee_telnet': {
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
            },
            'log_beekeeper': {
                'enabled': False,
                'beekeeper_url': 'https://127.0.0.1:5000/',
                'beekeeper_pass': beekeeper_password,
                'cert': cert_str
            },
        }
        config_json = json.dumps(config)

        db_session = database.get_session()
        f = Feeder(id=new_feeder_id, configuration=config_json)
        u = User(id=new_feeder_id, nickname='Feeder', password=beekeeper_password, utype=2)
        db_session.add_all([f, u])
        db_session.commit()
        config_link = '/ws/feeder/config/{0}'.format(new_feeder_id)
        iso_link = '/iso/feeder/{0}.iso'.format(new_feeder_id)
        return render_template('finish-config.html', mode_name='Feeder', user=current_user,
                               config_link=config_link, iso_link=iso_link)

    return render_template('create-config.html', form=form, mode_name='Feeder', user=current_user)


@app.route('/ws/feeder/delete', methods=['POST'])
@login_required
def delete_feeders():
    feeder_ids = json.loads(request.data)
    db_session = database.get_session()
    for feeder in feeder_ids:
        feeder_id = feeder['feeder_id']
        to_delete = db_session.query(Feeder).filter(Feeder.id == feeder_id).one()
        fuser = db_session.query(User).filter(User.id == feeder_id).one()
        for b in to_delete.honeybees:
            db_session.delete(b)
        db_session.delete(to_delete)
        db_session.delete(fuser)
    db_session.commit()
    return ''


@app.route('/data/sessions/all', methods=['GET', 'POST'])
@login_required
def data_sessions_all():
    db_session = database.get_session()
    sessions = db_session.query(Session).all()
    rows = []
    for s in sessions:
        row = {'time': s.timestamp.strftime('%Y-%m-%d %H:%M:%S'), 'protocol': s.protocol, 'ip_address': s.source_ip}
        rows.append(row)
    rsp = Response(response=json.dumps(rows, indent=4), status=200, mimetype='application/json')
    return rsp


@app.route('/data/sessions/honeybees', methods=['GET', 'POST'])
@login_required
def data_sessions_bees():
    db_session = database.get_session()
    honeybees = db_session.query(Honeybee).all()
    rows = []
    for b in honeybees:
        row = {'time': b.timestamp.strftime('%Y-%m-%d %H:%M:%S'), 'protocol': b.protocol, 'ip_address': b.source_ip}
        rows.append(row)
    rsp = Response(response=json.dumps(rows, indent=4), status=200, mimetype='application/json')
    return rsp


@app.route('/data/sessions/attacks', methods=['GET', 'POST'])
@login_required
def data_sessions_attacks():
    db_session = database.get_session()
    attacks = db_session.query(Session).filter(Session.classification_id != 'honeybee').all()
    rows = []
    for a in attacks:
        row = {'time': a.timestamp.strftime('%Y-%m-%d %H:%M:%S'), 'protocol': a.protocol, 'ip_address': a.source_ip}
        rows.append(row)
    rsp = Response(response=json.dumps(rows, indent=4), status=200, mimetype='application/json')
    return rsp


@app.route('/data/hives', methods=['GET'])
@login_required
def data_hives():
    db_session = database.get_session()
    hives = db_session.query(Hive).all()
    rows = []
    for h in hives:
        row = {'hive_id': h.id, 'attacks': db_session.query(Session).filter(Session.hive_id == h.id).count(),
               'checked': False}
        rows.append(row)
    rsp = Response(response=json.dumps(rows, indent=4), status=200, mimetype='application/json')
    return rsp


@app.route('/data/feeders', methods=['GET'])
@login_required
def data_feeders():
    db_session = database.get_session()
    feeders = db_session.query(Feeder).all()
    rows = []
    for f in feeders:
        row = {'feeder_id': f.id, 'bees': db_session.query(Honeybee).filter(Honeybee.feeder_id == f.id).count(),
               'checked': False}
        rows.append(row)
    rsp = Response(response=json.dumps(rows, indent=4), status=200, mimetype='application/json')
    return rsp


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_session = database.get_session()
        user = None
        try:
            user = db_session.query(User).filter(User.id == form.username.data).one()
        except NoResultFound:
            logging.info('Attempt to log in as non-existant user: {0}'.format(form.username.data))
        if user:
            if user.utype != 0:
                if form.password.data == user.password:
                    login_user(user)
                    logging.info('User {0} logged in.'.format(user.id))
                    flash('Logged in successfully')
                    return redirect(request.args.get("next") or '/')
            elif check_password_hash(user.password, form.password.data):
                login_user(user)
                logging.info('User {0} logged in.'.format(user.id))
                flash('Logged in successfully')
                return redirect(request.args.get("next") or '/')
    return render_template('login.html', form=form)


@app.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    flash('Logged out succesfully')
    return redirect('/login')


@app.route('/iso/hive/<hive_id>.iso', methods=['GET'])
@login_required
def generate_hive_iso(hive_id):
    logging.info('Generating new ISO for Hive ({})'.format(hive_id))
    db_session = database.get_session()
    current_hive = db_session.query(Hive).filter(Hive.id == hive_id).one()

    tempdir = tempfile.mkdtemp()
    custom_config_dir = os.path.join(tempdir, 'custom_config')
    os.makedirs(custom_config_dir)

    package_directory = os.path.dirname(os.path.abspath(beeswarm.__file__))
    logging.debug('Copying data files to temporary directory.')
    shutil.copytree(os.path.join(package_directory, 'hive/data'), os.path.join(custom_config_dir, 'data/'))

    config_file_path = os.path.join(custom_config_dir, 'hivecfg.json')
    with open(config_file_path, 'w') as config_file:
        config_file.write(current_hive.configuration)

    if not write_to_iso(tempdir, current_hive.id):
        return 'Not Found', 404
    return send_from_directory(tempdir, 'custom.iso', mimetype='application/iso-image')


@app.route('/iso/feeder/<feeder_id>.iso', methods=['GET'])
@login_required
def generate_feeder_iso(feeder_id):
    logging.info('Generating new ISO for Feeder ({})'.format(feeder_id))
    db_session = database.get_session()
    current_hive = db_session.query(Feeder).filter(Feeder.id == feeder_id).one()

    tempdir = tempfile.mkdtemp()
    custom_config_dir = os.path.join(tempdir, 'custom_config')
    os.makedirs(custom_config_dir)

    config_file_path = os.path.join(custom_config_dir, 'hivecfg.json')
    with open(config_file_path, 'w') as config_file:
        config_file.write(current_hive.configuration)

    if not write_to_iso(tempdir, current_hive.id):
        return 'Not Found', 404
    return send_from_directory(tempdir, 'custom.iso', mimetype='application/iso-image')


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    form = SettingsForm()

    if form.validate_on_submit():
        with open(app.config['BEEKEEPER_CONFIG'], 'r+') as config_file:
            config = json.load(config_file)
            config['honeybee_session_retain'] = form.honeybee_session_retain.data
            config['malicious_session_retain'] = form.malicious_session_retain.data
            #clear file
            config_file.seek(0)
            config_file.truncate(0)
            config_file.write(json.dumps(config, indent=4))

    return render_template('settings.html', form=form, user=current_user)


def write_to_iso(temporary_dir, mode_id):

    with open(app.config['BEEKEEPER_CONFIG'], 'r+') as config_file:
        config = json.load(config_file)
        iso_file_path = config['iso']['path']
        offset = int(config['iso']['write_offset'], 16)

    if not iso_file_path:
        logging.warning('No base ISO path specified.')
        return False

    custom_config_dir = os.path.join(temporary_dir, 'custom_config')

    # Change directory to create the tar archive in the temp directory
    save_cwd = os.getcwd()
    os.chdir(temporary_dir)
    config_archive = shutil.make_archive(mode_id, 'gztar', custom_config_dir)
    # Change it back
    os.chdir(save_cwd)

    temp_iso_path = os.path.join(temporary_dir, 'custom.iso')
    shutil.copyfile(iso_file_path, temp_iso_path)

    with open(temp_iso_path, 'r+b') as isofile:
        isofile.seek(offset)
        with open(config_archive, 'rb') as tarfile:
            isofile.write(tarfile.read())

    return True

if __name__ == '__main__':
    app.run()
