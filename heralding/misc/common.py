# Copyright (C) 2017 Johnny Vestergaard <jkv@unixcluster.dk>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
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
            os._exit(1)


async def cancel_all_pending_tasks(loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()
    pending = asyncio.Task.all_tasks(loop=loop)
    pending.remove(asyncio.Task.current_task(loop=loop))
    for task in pending:
        # We give task only 1 second to die.
        task.cancel()
        try:
            await asyncio.wait_for(task, timeout=1, loop=loop)
        except (asyncio.CancelledError, KeyboardInterrupt, ConnectionResetError):
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
