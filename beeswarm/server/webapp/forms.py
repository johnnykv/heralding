from flask.ext.wtf import Form
from wtforms import IntegerField, PasswordField, TextField, BooleanField, ValidationError, validators
from wtforms.validators import Required, Length


def validate_time_range(form, field):
    """ Makes sure the form data is in 'hh:mm - hh:mm' format and  the start time is less than end time."""

    string = field.data
    try:
        begin, end = string.split('-')
        begin = begin.strip()
        end = end.strip()
        begin_hours, begin_min = begin.split(':')
        end_hours, end_min = end.split(':')
        assert 0 <= int(begin_hours) <= 23
        assert 0 <= int(end_hours) <= 23
        assert 0 <= int(begin_min) <= 59
        assert 0 <= int(end_min) <= 59
        assert begin_hours <= end_hours
        if begin_hours == end_hours:
            assert begin_min < end_min
    except (ValueError, AssertionError):
        raise ValidationError('Make sure the time is in correct format: "hh:mm - hh:mm"')


class HoneypotConfigurationForm(Form):
    general__name = TextField(default='', label='Name')

    # __ splits make lookup in dictionary possible

    capabilities__http__enabled = BooleanField(default=False, label='Enabled')
    capabilities__http__port = IntegerField(default=80, label='Port')
    capabilities__http__protocol_specific_data__banner = TextField(default='Microsoft-IIS/5.0', label='Server Banner')

    capabilities__https__enabled = BooleanField(default=False, label='Enabled')
    capabilities__https__port = IntegerField(default=443, label='Port')
    capabilities__https__protocol_specific_data__banner = TextField(default='Microsoft-IIS/5.0', label='Server Banner')

    capabilities__ftp__enabled = BooleanField(default=False, label='Enabled')
    capabilities__ftp__port = IntegerField(default=21, label='Port')
    capabilities__ftp__protocol_specific_data__max_attempts = IntegerField(default=3, label='Login Attempts')
    capabilities__ftp__protocol_specific_data__syst_type = TextField(default='Windows-NT', label='System Type')
    capabilities__ftp__protocol_specific_data__banner = TextField(default='Microsoft FTP Server', label='Server Banner')

    capabilities__smtp__enabled = BooleanField(default=False, label='Enabled')
    capabilities__smtp__port = IntegerField(default=25, label='Port')
    capabilities__smtp__protocol_specific_data__banner = TextField(default='Microsoft ESMTP MAIL service ready',
                                                                   label='Server Banner')

    capabilities__vnc__enabled = BooleanField(default=False, label='Enabled')
    capabilities__vnc__port = IntegerField(default=5900, label='Port')

    capabilities__telnet__enabled = BooleanField(default=False, label='Enabled')
    capabilities__telnet__port = IntegerField(default=23, label='Port')
    capabilities__telnet__protocol_specific_data__max_attempts = IntegerField(default=3, label='Login Attempts')

    capabilities__pop3__enabled = BooleanField(default=False, label='Enabled')
    capabilities__pop3__port = IntegerField(default=110, label='Port')
    capabilities__pop3__protocol_specific_data__max_attempts = IntegerField(default=3, label='Login Attempts')

    capabilities__pop3s__enabled = BooleanField(default=False, label='Enabled')
    capabilities__pop3s__port = IntegerField(default=995, label='Port')
    capabilities__pop3s__protocol_specific_data__max_attempts = IntegerField(default=3, label='Login Attempts')

    capabilities__ssh__enabled = BooleanField(default=False, label='Enabled')
    capabilities__ssh__port = IntegerField(default=22, label='Port')

    certificate_info__common_name = TextField(default='', label='Common Name/Domain name',
                                              description='Leave this field empty to force the drone to automatically use  it\'s own IP '
                                                          'address when creating the certificate')
    certificate_info__country = TextField(validators=[Required(), Length(min=2, max=2)], label='Country')
    certificate_info__state = TextField(validators=[Required(), Length(min=1, max=64)], label='State')
    certificate_info__organization = TextField(validators=[Required(), Length(min=1, max=64)], label='Organization')
    certificate_info__organization_unit = TextField(default='', label='Organization Unit')
    certificate_info__locality = TextField(validators=[Required(), Length(min=1, max=64)], label='Locality')


class NewClientConfigForm(Form):
    http_active_range = TextField(validators=[validate_time_range], default='00:00 - 23:59',
                                  description='<small><em>hh:mm - hh:mm</em></small>', label='Activity Time')
    http_sleep_interval = TextField(default=720, label='Sleep Interval')
    http_activation_probability = TextField(default=0.4, label='Activation Probability')

    https_active_range = TextField(validators=[validate_time_range], default='00:00 - 23:59',
                                   description='<small><em>hh:mm - hh:mm</em></small>', label='Activity Time')
    https_sleep_interval = TextField(default=720, label='Sleep Interval')
    https_activation_probability = TextField(default=0.4, label='Activation Probability')

    pop3_active_range = TextField(validators=[validate_time_range], default='00:00 - 23:59',
                                  description='<small><em>hh:mm - hh:mm</em></small>', label='Activity Time')
    pop3_sleep_interval = TextField(default=720, label='Sleep Interval')
    pop3_activation_probability = TextField(default=0.4, label='Activation Probability')

    pop3s_active_range = TextField(validators=[validate_time_range], default='00:00 - 23:59',
                                   description='<small><em>hh:mm - hh:mm</em></small>', label='Activity Time')
    pop3s_sleep_interval = TextField(default=720, label='Sleep Interval')
    pop3s_activation_probability = TextField(default=0.4, label='Activation Probability')

    smtp_active_range = TextField(validators=[validate_time_range], default='00:00 - 23:59',
                                  description='<small><em>hh:mm - hh:mm</em></small>', label='Activity Time')
    smtp_sleep_interval = TextField(default=720, label='Sleep Interval')
    smtp_activation_probability = TextField(default=0.4, label='Activation Probability')

    vnc_active_range = TextField(validators=[validate_time_range], default='00:00 - 23:59',
                                 description='<small><em>hh:mm - hh:mm</em></small>', label='Activity Time')
    vnc_sleep_interval = TextField(default=720, label='Sleep Interval')
    vnc_activation_probability = TextField(default=0.4, label='Activation Probability')

    telnet_active_range = TextField(validators=[validate_time_range], default='00:00 - 23:59',
                                    description='<small><em>hh:mm - hh:mm</em></small>', label='Activity Time')
    telnet_sleep_interval = TextField(default=720, label='Sleep Interval')
    telnet_activation_probability = TextField(default=0.4, label='Activation Probability')

    ssh_active_range = TextField(validators=[validate_time_range], default='00:00 - 23:59',
                                 description='<small><em>hh:mm - hh:mm</em></small>', label='Activity Time')
    ssh_sleep_interval = TextField(default=720, label='Sleep Interval')
    ssh_activation_probability = TextField(default=0.4, label='Activation Probability')

    ftp_active_range = TextField(validators=[validate_time_range], default='00:00 - 23:59',
                                 description='<small><em>hh:mm - hh:mm</em></small>', label='Activity Time')
    ftp_sleep_interval = TextField(default=720, label='Sleep Interval')
    ftp_activation_probability = TextField(default=0.4, label='Activation Probability')


class LoginForm(Form):
    username = TextField()
    password = PasswordField()


class SettingsForm(Form):
    bait_session_retain = IntegerField('Bait session retention', default=2,
                                       description='<small><em>days until legit bait_sessions are deleted.</em></small>',
                                       validators=[validators.required(message=u'This field is required'),
                                                   validators.NumberRange(min=1)])

    malicious_session_retain = IntegerField('Malicious session retention', default=100,
                                            description='<small><em>days until malicious sessions are deleted</em></small>',
                                            validators=[validators.required(message=u'This field is required'),
                                                        validators.NumberRange(min=1)])

    ignore_failed_bait_session = BooleanField('Ignore failed bait_sessions', default=True,
                                              description='<small><em>Ignore bait_sessions that did not connect</em></small>')
