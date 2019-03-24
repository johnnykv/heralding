class FeedException(Exception):
    pass


class Disconnect(Exception):
    pass


class ProtocolException(Disconnect):
    pass


class MessageTooBig(ProtocolException):

    def __init__(self, op, ml, max_ml):
        super(MessageTooBig, self).__init__(
            'Message too big; op {op} ml: {ml} max_ml: {max_ml}'.format(
                op=op,
                ml=ml,
                max_ml=max_ml,
            )
        )


class BadClient(ProtocolException):
    pass
