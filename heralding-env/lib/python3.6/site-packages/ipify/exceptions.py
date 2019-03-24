"""
ipify.exceptions
~~~~~~~~~~~~~~~~

This module contains all ipify exceptions.
"""


class IpifyException(Exception):
    """
    There was an ambiguous exception that occurred while attempting to fetch
    your machine's public IP address from the ipify service.
    """
    pass


class ServiceError(IpifyException):
    """
    The request failed because the ipify service is currently down or
    experiencing issues.
    """
    pass


class ConnectionError(IpifyException):
    """
    The request failed because it wasn't able to reach the ipify service.  This
    is most likely due to a networking error of some sort.
    """
    pass
