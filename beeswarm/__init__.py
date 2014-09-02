try:
    import zmq.green as zmq
    zmq_context = zmq.Context()
except ImportError:
    pass

version = '0.4.16'

