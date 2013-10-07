from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship

Base = declarative_base()


class Feeder(Base):
    __tablename__ = 'feeder'
    id = Column(String, primary_key=True)
    honeybees = relationship("Honeybee", backref='Feeder')
    configuration = Column(String)


class Hive(Base):
    __tablename__ = 'hive'
    id = Column(String, primary_key=True)
    sessions = relationship("Session", backref='Hive')
    configuration = Column(String)


class Classification(Base):
    __tablename__ = 'classification'
    type = Column(String, primary_key=True)
    description_long = Column(String)
    description_short = Column(String)


class Session(Base):
    __tablename__ = 'session'
    id = Column(String, primary_key=True)
    discriminator = Column('type', String(50))
    __mapper_args__ = {'polymorphic_on': discriminator}
    received = Column(DateTime)
    timestamp = Column(DateTime)
    protocol = Column(String)
    authentication = relationship('Authentication')
    source_ip = Column(String)
    source_port = Column(Integer)
    session_data = relationship('SessionData', backref='Session')
    transcript = relationship('Transcript', uselist=False, backref='Session')
    destination_ip = Column(String)
    destination_port = Column(Integer)
    hive_id = Column(String, ForeignKey('hive.id'))
    hive = relationship('Hive')
    classification_id = Column(String, ForeignKey('classification.type'), nullable=False, default='unclassified')
    classification = relationship('Classification')


class Authentication(Base):
    __tablename__ = 'authentication'
    id = Column(String, primary_key=True)
    timestamp = Column(DateTime)
    username = Column(String)
    password = Column(String)
    successful = Column(Boolean)
    session_id = Column(String, ForeignKey('session.id'))
    session = relationship('Session')


class SessionData(Base):
    __tablename__ = 'sessiondata'
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String)
    data = Column(String)
    session_id = Column(String, ForeignKey('session.id'))
    session = relationship('Session')


class Transcript(Base):
    __tablename__ = 'transcript'
    id = Column(Integer, primary_key=True, autoincrement=True)
    data = Column(String)
    session_id = Column(String, ForeignKey('session.id'))


class Honeybee(Session):
    __tablename__ = 'honeybee'
    __mapper_args__ = {'polymorphic_identity': 'honeybee'}
    id = Column(String, ForeignKey('session.id'), primary_key=True)
    did_connect = Column(Boolean)
    did_login = Column(Boolean)
    did_complete = Column(Boolean)
    feeder_id = Column(String, ForeignKey('feeder.id'))
    feeder = relationship('Feeder')


class User(Base):
    __tablename__ = 'user'
    id = Column(String(32), primary_key=True)
    nickname = Column(String(64))
    password = Column(String(256))

    # User type will be:
    # Admin  == 0
    # Hive   == 1
    # Feeder == 2
    utype = Column(Integer, default=0)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)

    def __repr__(self):
        return '<User %r>' % self.nickname


class HiveUser(Base):
    __tablename__ = 'hiveuser'
    username = Column(String(32), primary_key=True)
    password = Column(String(32))
