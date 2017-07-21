import sys
import logging
import asyncio

from OpenSSL import crypto
from Crypto.PublicKey import RSA

logger = logging.getLogger(__name__)


def on_unhandled_task_exception(task):
    if not task.cancelled():
        task_exc = task.exception()
        if task_exc:
            logger.error('Stopping because {0} died: {1}'.format(task, task_exc))
            sys.exit(1)


def cancel_all_pending_tasks(loop):
    pending = asyncio.Task.all_tasks(loop=loop)
    for task in pending:
        task.cancel()
        try:
            loop.run_until_complete(task)
        except asyncio.CancelledError:
            pass


def generate_self_signed_cert(cert_country, cert_state, cert_organization, cert_locality, cert_organizational_unit,
                              cert_common_name, valid_days, serial_number):
    rsa_key = RSA.generate(2048)

    pk = crypto.load_privatekey(crypto.FILETYPE_PEM, rsa_key.exportKey('PEM', pkcs=1))
    cert = crypto.X509()
    sub = cert.get_subject()
    sub.CN = cert_common_name
    sub.C = cert_country
    sub.ST = cert_state
    sub.L = cert_locality
    sub.O = cert_organization

    # optional
    if cert_organizational_unit:
        sub.OU = cert_organizational_unit

    cert.set_serial_number(serial_number)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(valid_days * 24 * 60 * 60)  # Valid for a year
    cert.set_issuer(sub)
    cert.set_pubkey(pk)
    cert.sign(pk, 'sha1')

    cert_text = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
    priv_key_text = rsa_key.exportKey('PEM', pkcs=1)

    return cert_text, priv_key_text
