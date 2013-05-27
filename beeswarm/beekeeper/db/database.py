from datetime import datetime
from pony.orm import *
from pony.orm.core import Discriminator
from beeswarm.beekeeper.db.database_config import db

#db = Database("sqlite", "beekeeper.sqlite", create_db=True)

if db is None:
    raise OperationalError('Please setup database before importing this module.')


class Feeder(db.Entity):
    id = PrimaryKey(str)
    honeybees = Set("Honeybee")


class Session(db.Entity):
    classtype = Discriminator(int)
    id = PrimaryKey(str)
    received = Required(datetime)
    timestamp = Required(datetime)
    protocol = Required(str)
    username = Optional(unicode)
    password = Optional(unicode)
    source_ip = Required(str)
    source_port = Required(int)
    destination_ip = Required(str)
    destination_port = Required(int)
    hive = Optional("Hive")
    classification = Optional("Classification")


class Hive(db.Entity):
    id = PrimaryKey(str)
    sessions = Set(Session)


class Honeybee(db.Session):
    feeder = Required(Feeder)
    did_connect = Optional(bool)
    did_login = Optional(bool)
    did_complete = Optional(bool)


class Classification(db.Entity):
    type = PrimaryKey(str)
    sessions = Set(Session)
    description_long = Required(str)
    description_short = Required(str)


#sql_debug(True)
db.generate_mapping(create_tables=True)
# db.generate_mapping(check_tables=True)