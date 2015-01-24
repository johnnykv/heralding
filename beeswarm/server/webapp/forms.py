from flask.ext.wtf import Form
from wtforms import IntegerField, PasswordField, StringField, BooleanField, ValidationError, validators, FloatField
from wtforms.validators import DataRequired, Length


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
    general__name = StringField(default='', label='Name')

    # __ splits make lookup in dictionary possible

    port_validators = [validators.NumberRange(min=0, max=65335, message='Must be between 0 and 65335.')]

    capabilities__http__enabled = BooleanField(default=False, label='Enabled')
    capabilities__http__port = IntegerField(default=80, label='Port', validators=port_validators)
    capabilities__http__protocol_specific_data__banner = StringField(default='Microsoft-IIS/5.0', label='Server Banner')

    capabilities__https__enabled = BooleanField(default=False, label='Enabled')
    capabilities__https__port = IntegerField(default=443, validators=port_validators)
    capabilities__https__protocol_specific_data__banner = StringField(default='Microsoft-IIS/5.0',
                                                                      label='Server Banner')

    capabilities__ftp__enabled = BooleanField(default=False, label='Enabled')
    capabilities__ftp__port = IntegerField(default=21, validators=port_validators)
    capabilities__ftp__protocol_specific_data__max_attempts = IntegerField(default=3, label='Login Attempts')
    capabilities__ftp__protocol_specific_data__syst_type = StringField(default='Windows-NT', label='System Type')
    capabilities__ftp__protocol_specific_data__banner = StringField(default='Microsoft FTP Server',
                                                                    label='Server Banner')

    capabilities__smtp__enabled = BooleanField(default=False, label='Enabled')
    capabilities__smtp__port = IntegerField(default=25, validators=port_validators)
    capabilities__smtp__protocol_specific_data__banner = StringField(default='Microsoft ESMTP MAIL service ready',
                                                                     label='Server Banner')

    capabilities__vnc__enabled = BooleanField(default=False, label='Enabled')
    capabilities__vnc__port = IntegerField(default=5900, validators=port_validators)

    capabilities__telnet__enabled = BooleanField(default=False, label='Enabled')
    capabilities__telnet__port = IntegerField(default=23, validators=port_validators)
    capabilities__telnet__protocol_specific_data__max_attempts = IntegerField(default=3, label='Login Attempts')

    capabilities__pop3__enabled = BooleanField(default=False, label='Enabled')
    capabilities__pop3__port = IntegerField(default=110, validators=port_validators)
    capabilities__pop3__protocol_specific_data__max_attempts = IntegerField(default=3, label='Login Attempts')

    capabilities__pop3s__enabled = BooleanField(default=False, label='Enabled')
    capabilities__pop3s__port = IntegerField(default=995, validators=port_validators)
    capabilities__pop3s__protocol_specific_data__max_attempts = IntegerField(default=3, label='Login Attempts')

    capabilities__ssh__enabled = BooleanField(default=False, label='Enabled')
    capabilities__ssh__port = IntegerField(default=22, validators=port_validators)

    certificate_info__common_name = StringField(default='', label='Common Name/Domain name',
                                                description='Leave this field empty to force the drone to automatically use  it\'s own IP '
                                                            'address when creating the certificate')
    certificate_info__country = StringField(validators=[DataRequired(), Length(min=2, max=2)], label='Country')
    certificate_info__state = StringField(validators=[DataRequired(), Length(min=1, max=64)], label='State')
    certificate_info__organization = StringField(validators=[DataRequired(), Length(min=1, max=64)],
                                                 label='Organization')
    certificate_info__organization_unit = StringField(default='', label='Organization Unit')
    certificate_info__locality = StringField(validators=[DataRequired(), Length(min=1, max=64)], label='Locality')


class ClientConfigurationForm(Form):
    active_range_description = '<small><em>hh:mm - hh:mm</br>The period of the day where this bait type will get ' \
                               'evaluated for transmission</em></small>'
    interval_description = '<small><em>Seconds to sleep between each transmission decision evaluation</em></small>'
    probability_description = '<small><em>0.0 - 0.1.</br> The probability that a given bait session will be transmitted ' \
                              'after waking up.</br>Set to 1 to always transmit </em></small>'

    general__name = StringField(default='', label='Name')
    sleep_interval_validators = [validators.NumberRange(min=0, max=43000, message='Must be between 0 and 43000.')]
    probability_validators = [validators.NumberRange(min=0, max=1, message='Must be between 0.0 and 1.')]

    bait_timings__http__active_range = StringField(validators=[validate_time_range], default='00:00 - 23:59',
                                                   description=active_range_description,
                                                   label='Activity Time')
    bait_timings__http__sleep_interval = IntegerField(default=120, label='Sleep Interval',
                                                      validators=sleep_interval_validators,
                                                      description=interval_description)
    bait_timings__http__activation_probability = FloatField(default=1, label='Activation Probability',
                                                            description=probability_description,
                                                            validators=probability_validators)

    bait_timings__https__active_range = StringField(validators=[validate_time_range], default='00:00 - 23:59',
                                                    description=active_range_description,
                                                    label='Activity Time')
    bait_timings__https__sleep_interval = IntegerField(default=120, label='Sleep Interval',
                                                       validators=sleep_interval_validators,
                                                       description=interval_description)
    bait_timings__https__activation_probability = FloatField(default=1, label='Activation Probability',
                                                             description=probability_description,
                                                             validators=probability_validators)

    bait_timings__pop3__active_range = StringField(validators=[validate_time_range], default='00:00 - 23:59',
                                                   description=active_range_description,
                                                   label='Activity Time')
    bait_timings__pop3__sleep_interval = IntegerField(default=120, label='Sleep Interval',
                                                      validators=sleep_interval_validators,
                                                      description=interval_description)
    bait_timings__pop3__activation_probability = FloatField(default=1, label='Activation Probability',
                                                            description=probability_description,
                                                            validators=probability_validators)

    bait_timings__pop3s__active_range = StringField(validators=[validate_time_range], default='00:00 - 23:59',
                                                    description=active_range_description,
                                                    label='Activity Time')
    bait_timings__pop3s__sleep_interval = IntegerField(default=120, label='Sleep Interval',
                                                       validators=sleep_interval_validators,
                                                       description=interval_description)
    bait_timings__pop3s__activation_probability = FloatField(default=1, label='Activation Probability',
                                                             description=probability_description,
                                                             validators=probability_validators)

    bait_timings__smtp__active_range = StringField(validators=[validate_time_range], default='00:00 - 23:59',
                                                   description=active_range_description,
                                                   label='Activity Time')
    bait_timings__smtp__sleep_interval = IntegerField(default=120, label='Sleep Interval',
                                                      validators=sleep_interval_validators,
                                                      description=interval_description)
    bait_timings__smtp__activation_probability = FloatField(default=1, label='Activation Probability',
                                                            description=probability_description,
                                                            validators=probability_validators)

    bait_timings__vnc__active_range = StringField(validators=[validate_time_range], default='00:00 - 23:59',
                                                  description=active_range_description,
                                                  label='Activity Time')
    bait_timings__vnc__sleep_interval = IntegerField(default=120, label='Sleep Interval',
                                                     validators=sleep_interval_validators,
                                                     description=interval_description)
    bait_timings__vnc__activation_probability = FloatField(default=1, label='Activation Probability',
                                                           description=probability_description,
                                                           validators=probability_validators)

    bait_timings__telnet__active_range = StringField(validators=[validate_time_range], default='00:00 - 23:59',
                                                     description=active_range_description,
                                                     label='Activity Time')
    bait_timings__telnet__sleep_interval = IntegerField(default=120, label='Sleep Interval',
                                                        validators=sleep_interval_validators,
                                                        description=interval_description)
    bait_timings__telnet__activation_probability = FloatField(default=1, label='Activation Probability',
                                                              description=probability_description,
                                                              validators=probability_validators)

    bait_timings__ssh__active_range = StringField(validators=[validate_time_range], default='00:00 - 23:59',
                                                  description=active_range_description,
                                                  label='Activity Time')
    bait_timings__ssh__sleep_interval = IntegerField(default=120, label='Sleep Interval',
                                                     validators=sleep_interval_validators,
                                                     description=interval_description)
    bait_timings__ssh__activation_probability = FloatField(default=1, label='Activation Probability',
                                                           description=probability_description,
                                                           validators=probability_validators)

    bait_timings__ftp__active_range = StringField(validators=[validate_time_range], default='00:00 - 23:59',
                                                  description=active_range_description,
                                                  label='Activity Time')
    bait_timings__ftp__sleep_interval = IntegerField(default=120, label='Sleep Interval',
                                                     validators=sleep_interval_validators,
                                                     description=interval_description)
    bait_timings__ftp__activation_probability = FloatField(default=1, label='Activation Probability',
                                                           description=probability_description,
                                                           validators=probability_validators)


class LoginForm(Form):
    username = StringField()
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
