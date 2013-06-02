from flask.ext.wtf import Form, TextField, BooleanField, RadioField
from flask.ext.wtf import Required
from flask.ext.wtf import IntegerField, FileField


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
    pop3s_port = IntegerField(default=110)
    pop3s_max_attempts = IntegerField(default=3)

    ssh_enabled = BooleanField(default=False)
    ssh_port = IntegerField(default=22)
    ssh_key = FileField(default='server.key')


class NewFeederConfigForm(Form):

    http_enabled = BooleanField(default=False)
    http_server = TextField(default='127.0.0.1')
    http_port = IntegerField(default=80)
    http_timing = TextField(default='regular')
    http_login = TextField(default='test')
    http_password = TextField(default='password')

    pop3_enabled = BooleanField(default=False)
    pop3_server = TextField(default='127.0.0.1')
    pop3_port = IntegerField(default=110)
    pop3_timing = TextField(default='regular')
    pop3_login = TextField(default='test')
    pop3_password = TextField(default='password')

    smtp_enabled = BooleanField(default=False)
    smtp_server = TextField(default='127.0.0.1')
    smtp_port = IntegerField(default=25)
    smtp_timing = TextField(default='regular')
    smtp_login = TextField(default='test')
    smtp_password = TextField(default='password')

    vnc_enabled = BooleanField(default=False)
    vnc_server = TextField(default='127.0.0.1')
    vnc_port = IntegerField(default=5900)
    vnc_timing = TextField(default='regular')
    vnc_login = TextField(default='test')
    vnc_password = TextField(default='password')

    telnet_enabled = BooleanField(default=False)
    telnet_server = TextField(default='127.0.0.1')
    telnet_port = IntegerField(default=23)
    telnet_timing = TextField(default='regular')
    telnet_login = TextField(default='test')
    telnet_password = TextField(default='password')

    ftp_enabled = BooleanField(default=False)
    ftp_server = TextField(default='127.0.0.1')
    ftp_port = IntegerField(default=21)
    ftp_timing = TextField(default='regular')
    ftp_login = TextField(default='test')
    ftp_password = TextField(default='password')
