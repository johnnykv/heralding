import datetime
import json

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Table, Float
from sqlalchemy.orm import relationship


Base = declarative_base()

# table for honeypot <-> client many to many relationship
honeypot_client_mtm = Table('association', Base.metadata,
                            Column('client', String, ForeignKey('client.id')),
                            Column('honeypot', String, ForeignKey('honeypot.id')))


class Capability(Base):
    __tablename__ = 'capability'
    id = Column(Integer, primary_key=True, autoincrement=True)
    honeypot_id = Column(String, ForeignKey('honeypot.id'))
    protocol = Column(String)
    port = Column(Integer)
    # jsonified python dict
    protocol_specific_data = Column(String)
    baits = relationship("DroneEdge", cascade="all, delete-orphan", backref="capability")


class Drone(Base):
    __tablename__ = 'drone'
    discriminator = Column('type', String(50))
    __mapper_args__ = {'polymorphic_on': discriminator}

    id = Column(String, primary_key=True)
    name = Column(String, default='')
    ip_address = Column(String, default='')
    zmq_public_key = Column(String)
    zmq_private_key = Column(String)
    configuration = Column(String)
    last_activity = Column(DateTime, default=datetime.datetime.min)


# edge between honeypot and client
class DroneEdge(Base):
    __tablename__ = 'droneedge'
    client_id = Column(String, ForeignKey('drone.id'), primary_key=True)
    capability_id = Column(Integer, ForeignKey('capability.id'), primary_key=True)
    activation_range = Column(String)
    sleep_interval = Column(Integer)
    activation_probability = Column(Float)
    username = Column(String)
    password = Column(String)


class Client(Drone):
    __tablename__ = 'client'
    __mapper_args__ = {'polymorphic_identity': 'client'}

    id = Column(String, ForeignKey('drone.id'), primary_key=True)
    bait_sessions = relationship("BaitSession", cascade="all, delete-orphan", backref='client')

    baits = relationship('DroneEdge', cascade='all, delete-orphan', backref='client')

    def add_bait(self, capability, activation_range, sleep_interval, activation_probability, username, password):
        bait = DroneEdge(capability=capability, activation_range=activation_range, sleep_interval=sleep_interval,
                         activation_probability=activation_probability, username=username, password=password)
        bait.client_id = self.id
        self.baits.append(bait)


class Classification(Base):
    __tablename__ = 'classification'
    type = Column(String, primary_key=True)
    description_long = Column(String)
    description_short = Column(String)


class Session(Base):
    __tablename__ = 'session'
    discriminator = Column('type', String(50))
    __mapper_args__ = {'polymorphic_on': discriminator}

    id = Column(String, primary_key=True)
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


class BaitSession(Session):
    __tablename__ = 'bait_session'
    __mapper_args__ = {'polymorphic_identity': 'bait_session'}

    id = Column(String, ForeignKey('session.id'), primary_key=True)
    did_connect = Column(Boolean)
    did_login = Column(Boolean)
    did_complete = Column(Boolean)
    client_id = Column(String, ForeignKey('client.id'))


class Honeypot(Drone):
    __tablename__ = 'honeypot'
    id = Column(String, ForeignKey('drone.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'honeypot'}

    sessions = relationship('Session', cascade='all, delete-orphan', backref='honeypot')
    clients = relationship('Client', secondary=honeypot_client_mtm)
    # current capabilities
    capabilities = relationship('Capability', cascade='all, delete-orphan', backref='honeypot')
    # fingerprint of the public key used to interact with attackers and clients
    cert_digest = Column(String)

    # The following certificate attribute are temporarily
    # generation of certificate should be done on the server, hence no need for
    #  this informaiton here
    cert_common_name = Column(String)
    cert_country = Column(String)
    cert_state = Column(String)
    cert_locality = Column(String)
    cert_organization = Column(String)
    cert_organization_unit = Column(String)

    def add_capability(self, protocol, port, protocol_specific_data):
        capability = Capability(protocol=protocol, port=port, protocol_specific_data=json.dumps(protocol_specific_data))
        self.capabilities.append(capability)


class User(Base):
    __tablename__ = 'user'

    id = Column(String(32), primary_key=True)
    nickname = Column(String(64))
    password = Column(String(256))

    # User type will be:
    # Admin  == 0

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

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(32))
    password = Column(String(32))