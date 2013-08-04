from flask.ext.wtf import Form, TextField, BooleanField
from flask.ext.wtf import IntegerField, FileField
from wtforms import PasswordField


class NewHiveConfigForm(Form):

    http_enabled = BooleanField(default=False)
    http_port = IntegerField(default=80)
    http_banner = TextField(default='Microsoft-IIS/5.0')

    https_enabled = BooleanField(default=False)
    https_port = IntegerField(default=443)
    https_banner = TextField(default='Microsoft-IIS/5.0')

    ftp_enabled = BooleanField(default=False)
    ftp_port = IntegerField(default=21)
    ftp_max_attempts = IntegerField(default=3)
    ftp_syst_type = TextField(default='Windows-NT')
    ftp_banner = TextField(default='Microsoft FTP Server')

    smtp_enabled = BooleanField(default=False)
    smtp_port = IntegerField(default=25)
    smtp_banner = TextField(default='Microsoft ESMTP MAIL service ready')

    vnc_enabled = BooleanField(default=False)
    vnc_port = IntegerField(default=5900)

    telnet_enabled = BooleanField(default=False)
    telnet_port = IntegerField(default=23)
    telnet_max_attempts = IntegerField(default=3)

    pop3_enabled = BooleanField(default=False)
    pop3_port = IntegerField(default=110)
    pop3_max_attempts = IntegerField(default=3)

    pop3s_enabled = BooleanField(default=False)
    pop3s_port = IntegerField(default=995)
    pop3s_max_attempts = IntegerField(default=3)

    ssh_enabled = BooleanField(default=False)
    ssh_port = IntegerField(default=22)
    ssh_key = FileField(default='server.key')


class NewFeederConfigForm(Form):

    http_enabled = BooleanField(default=False)
    http_server = TextField(default='127.0.0.1')
    http_port = IntegerField(default=80)
    http_active_range = TextField(default='00:00 - 23:59', description='<small><em>hh:mm - hh:mm</em></small>')
    http_sleep_interval = TextField(default=720)
    http_activation_probability = TextField(default=0.4)
    http_login = TextField(default='test')
    http_password = TextField(default='password')

    pop3_enabled = BooleanField(default=False)
    pop3_server = TextField(default='127.0.0.1')
    pop3_port = IntegerField(default=110)
    pop3_active_range = TextField(default='00:00 - 23:59', description='<small><em>hh:mm - hh:mm</em></small>')
    pop3_sleep_interval = TextField(default=720)
    pop3_activation_probability = TextField(default=0.4)
    pop3_login = TextField(default='test')
    pop3_password = TextField(default='password')

    pop3s_enabled = BooleanField(default=False)
    pop3s_server = TextField(default='127.0.0.1')
    pop3s_port = IntegerField(default=995)
    pop3s_active_range = TextField(default='00:00 - 23:59', description='<small><em>hh:mm - hh:mm</em></small>')
    pop3s_sleep_interval = TextField(default=720)
    pop3s_activation_probability = TextField(default=0.4)
    pop3s_login = TextField(default='test')
    pop3s_password = TextField(default='password')

    smtp_enabled = BooleanField(default=False)
    smtp_server = TextField(default='127.0.0.1')
    smtp_port = IntegerField(default=25)
    smtp_active_range = TextField(default='00:00 - 23:59', description='<small><em>hh:mm - hh:mm</em></small>')
    smtp_sleep_interval = TextField(default=720)
    smtp_activation_probability = TextField(default=0.4)
    smtp_login = TextField(default='test')
    smtp_local_hostname = TextField(default='localhost')
    smtp_password = TextField(default='password')

    vnc_enabled = BooleanField(default=False)
    vnc_server = TextField(default='127.0.0.1')
    vnc_port = IntegerField(default=5900)
    vnc_active_range = TextField(default='00:00 - 23:59', description='<small><em>hh:mm - hh:mm</em></small>')
    vnc_sleep_interval = TextField(default=720)
    vnc_activation_probability = TextField(default=0.4)
    vnc_login = TextField(default='test')
    vnc_password = TextField(default='password')

    telnet_enabled = BooleanField(default=False)
    telnet_server = TextField(default='127.0.0.1')
    telnet_port = IntegerField(default=23)
    telnet_active_range = TextField(default='00:00 - 23:59', description='<small><em>hh:mm - hh:mm</em></small>')
    telnet_sleep_interval = TextField(default=720)
    telnet_activation_probability = TextField(default=0.4)
    telnet_login = TextField(default='test')
    telnet_password = TextField(default='password')

    ssh_enabled = BooleanField(default=False)
    ssh_server = TextField(default='127.0.0.1')
    ssh_port = IntegerField(default=22)
    ssh_active_range = TextField(default='00:00 - 23:59', description='<small><em>hh:mm - hh:mm</em></small>')
    ssh_sleep_interval = TextField(default=720)
    ssh_activation_probability = TextField(default=0.4)
    ssh_login = TextField(default='test')
    ssh_password = TextField(default='password')

    ftp_enabled = BooleanField(default=False)
    ftp_server = TextField(default='127.0.0.1')
    ftp_port = IntegerField(default=21)
    ftp_active_range = TextField(default='00:00 - 23:59', description='<small><em>hh:mm - hh:mm</em></small>')
    ftp_sleep_interval = TextField(default=720)
    ftp_activation_probability = TextField(default=0.4)
    ftp_login = TextField(default='test')
    ftp_password = TextField(default='password')


class LoginForm(Form):

    username = TextField()
    password = PasswordField()
