from enum import Enum


class Messages(Enum):
    STOP = 'STOP'
    START = 'START'
    CONFIG = 'CONFIG'
    # dump of all configuration elements known to the sender
    CONFIG_FULL = 'CONFIG_FULL'
    # mapping between clients, honeypots, capabilities and bait users
    CONFIG_ARCHITECTURE = 'CONFIG_ARCHITECTURE'
    BROADCAST = 'BROADCAST'

    OK = 'OK'
    FAIL = 'FAIL'
    PUBLISH_CONFIG = 'PUBLISH_CONFIG'
    # KEY DRONE_ID DRONE_PRIVATE_KEY
    KEY = 'KEY'
    # CERT DRONE_ID DRONE_CERT
    CERT = 'CERT'
    SESSION_HONEYPOT = 'SESSION_HONEYPOT'
    SESSION_CLIENT = 'SESSION_CLIENT'
    SET = 'SET'
    GEN_ZMQ_KEYS = 'GEN_ZMQ_KEYS'
    PING = 'PING'
    PONG = 'PING'
    IP = 'IP'
