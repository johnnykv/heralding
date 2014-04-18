from enum import Enum


class Messages(Enum):
    STOP = 'STOP'
    START = 'START'
    CONFIG = 'CONFIG'
    BROADCAST = 'BROADCAST'
    OK = 'OK'
    FAIL = 'FAIL'
    PUBLISH_CONFIG = 'PUBLISH_CONFIG'
