from enum import Enum


class SocketNames(Enum):
    # As soon as sessions are received from the remote drone the data will get retransmitted unaltered on this socket
    RAW_PUBLISHER = 'inproc://rawSessionPublisher'
    # Request / Reply to config actor
    CONFIG_COMMANDS = 'inproc://configCommands'
    # After sessions has been classified they will get retransmitted on this socket.
    # TODO: Does not actually happen yet
    PROCESSES_SESSIONS = 'inproc://processedSessionPublisher'
    # Data sent on this socket will be retransmitted to the correct drone, the data must be prefixed with
    # the id of the drone.
    DRONE_COMMANDS = 'inproc://droneCommands'

    #### Sockets used on drones ####
    # Drone commands received from the server will be retransmitted  on this socket.
    SERVER_COMMANDS = 'inproc://serverCommands'
    # All messages transmitted on this socket will get retransmitted to the server
    SERVER_RELAY = 'inproc://serverRelay'
