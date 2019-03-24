"""
ipify.ipify
~~~~~~~~~~~

The module holds the main ipify library implementation.
"""


from backoff import expo, on_exception
from requests import get
from requests.exceptions import RequestException

from .exceptions import ConnectionError, ServiceError
from .settings import API_URI, MAX_TRIES, USER_AGENT


@on_exception(expo, RequestException, max_tries=MAX_TRIES)
def _get_ip_resp():
    """
    Internal function which attempts to retrieve this machine's public IP
    address from the ipify service (http://www.ipify.org).

    :rtype: obj
    :returns: The response object from the HTTP request.
    :raises: RequestException if something bad happened and the request wasn't
        completed.

    .. note::
        If an error occurs when making the HTTP request, it will be retried
        using an exponential backoff algorithm.  This is a safe way to retry
        failed requests without giving up.
    """
    return get(API_URI, headers={'user-agent': USER_AGENT})


def get_ip():
    """
    Query the ipify service (http://www.ipify.org) to retrieve this machine's
    public IP address.

    :rtype: string
    :returns: The public IP address of this machine as a string.
    :raises: ConnectionError if the request couldn't reach the ipify service,
        or ServiceError if there was a problem getting the IP address from
        ipify's service.
    """
    try:
        resp = _get_ip_resp()
    except RequestException:
        raise ConnectionError("The request failed because it wasn't able to reach the ipify service. This is most likely due to a networking error of some sort.")

    if resp.status_code != 200:
        raise ServiceError('Received an invalid status code from ipify:' + str(resp.status_code) + '. The service might be experiencing issues.')
    elif not resp.text:
        raise ServiceError('Received an response from ipify. The service might be experiencing issues.')

    return resp.text
