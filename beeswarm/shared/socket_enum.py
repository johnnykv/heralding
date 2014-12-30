from enum import Enum


class SocketNames(Enum):
    #### Sockets used on server ####
    # All data received from drones will be published on this socket
    DRONE_DATA = 'inproc://droneData'
    # After sessions has been classified they will get retransmitted on this socket.
    # TODO: Does not actually happen yet
    PROCESSED_SESSIONS = 'inproc://processedSessionPublisher'
    # Request / Reply to config actor
    CONFIG_COMMANDS = 'inproc://configCommands'
    # Data sent on this socket will be retransmitted to the correct drone, the data must be prefixed with
    # the id of the drone.
    DRONE_COMMANDS = 'inproc://droneCommands'


    # Requests to and from the databsae
    DATABASE_REQUESTS = 'inproc://databaseRequests'

    #### Sockets used on drones ####
    # Drone commands received from the server will be retransmitted  on this socket.
    SERVER_COMMANDS = 'inproc://serverCommands'
    # All messages transmitted on this socket will get retransmitted to the server
    SERVER_RELAY = 'inproc://serverRelay'
