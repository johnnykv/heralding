from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship

Base = declarative_base()

# table for honeypot <-> client many to many relationship
honeypot_client_mtm = Table('association', Base.metadata,
                            Column('client', String, ForeignKey('client.id')),
                            Column('honeypot', String, ForeignKey('honeypot.id')))


class Client(Base):
    __tablename__ = 'client'
    id = Column(String, primary_key=True)
    honeybees = relationship("Honeybee", cascade="all, delete-orphan", backref='client')
    # honeypots that this client will connect to.
    honeypots = relationship("Honeypot", secondary=honeypot_client_mtm)
    configuration = Column(String)


class Honeypot(Base):
    __tablename__ = 'honeypot'
    id = Column(String, primary_key=True)
    sessions = relationship("Session", cascade="all, delete-orphan", backref='honeypot')
    configuration = Column(String)
    clients = relationship("Client", secondary=honeypot_client_mtm)


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
    authentication = relationship('Authentication', cascade="all, delete-orphan")
    source_ip = Column(String)
    source_port = Column(Integer)
    session_data = relationship('SessionData', cascade="all, delete-orphan", backref='Session')
    transcript = relationship('Transcript', cascade="all, delete-orphan", backref='Session')
    destination_ip = Column(String)
    destination_port = Column(Integer)
    honeypot_id = Column(String, ForeignKey('honeypot.id'))
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
    direction = Column(String)
    timestamp = Column(DateTime)
    session_id = Column(String, ForeignKey('session.id'))


class Honeybee(Session):
    __tablename__ = 'honeybee'
    __mapper_args__ = {'polymorphic_identity': 'honeybee'}
    id = Column(String, ForeignKey('session.id'), primary_key=True)
    did_connect = Column(Boolean)
    did_login = Column(Boolean)
    did_complete = Column(Boolean)
    client_id = Column(String, ForeignKey('client.id'))


class User(Base):
    __tablename__ = 'user'
    id = Column(String(32), primary_key=True)
    nickname = Column(String(64))
    password = Column(String(256))

    # User type will be:
    # Admin  == 0
    # Honeypot   == 1
    # Client == 2
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


class BaitUser(Base):
    __tablename__ = 'baituser'
    username = Column(String(32), primary_key=True)
    password = Column(String(32))
