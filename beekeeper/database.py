from datetime import datetime
from pony.orm import *
from pony.orm.core import Discriminator
from db import db

class feeder(db.Entity):
    id = PrimaryKey(str)
    honeybees = Set("honeybee")


class session(db.Entity):
    classtype = Discriminator(int)
    id = PrimaryKey(str)
    timestamp = Required(datetime)
    protocol = Required(str)
    username = Optional(unicode)
    password = Optional(unicode)
    source_ip = Required(str)
    source_port = Required(int)
    destination_ip = Required(str)
    destination_port = Required(int)
    hive = Optional("hive")


class hive(db.Entity):
    id = PrimaryKey(str)
    sessions = Set(session)


class honeybee(db.session):
    feeder = Required(feeder)
    did_connect = Optional(bool)
    did_login = Optional(bool)
    did_complete = Optional(bool)

sql_debug(True)
db.generate_mapping(create_tables=True)