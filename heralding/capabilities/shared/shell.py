# pylint: disable-msg=E1101
# Copyright (C) 2013 Aniket Panse <contact@aniketpanse.in>
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

# Aniket Panse <contact@aniketpanse.in> grants Johnny Vestergaard <jkv@unixcluster.dk>
# a perpetual, worldwide, non-exclusive, no-charge, royalty-free, irrevocable
# copyright license to reproduce, prepare derivative works of, publicly
# display, publicly perform, sublicense, relicense, and distribute [the] Contributions
# and such derivative works.


import logging
import socket
import traceback

import gevent
from gevent.util import wrap_errors
from telnetsrv.green import TelnetHandler
from telnetsrv.telnetsrvlib import TelnetHandlerBase

logger = logging.getLogger(__name__)


class OwnGreenTelnetHandler(TelnetHandler):
    def setup(self):
        TelnetHandlerBase.setup(self)
        # Spawn a greenlet to handle socket input
        self.greenlet_ic = gevent.spawn(wrap_errors((socket.error), self.inputcooker))
        # Note that inputcooker exits on EOF

        # Sleep for 0.5 second to allow options negotiation
        gevent.sleep(0.5)


class Commands(OwnGreenTelnetHandler):
    """This class implements the shell functionality for the telnet and SSH capabilities"""

    max_tries = 3
    TERM = 'ansi'

    authNeedUser = True
    authNeedPass = True

    def __init__(self, request, client_address, server, session):
        self.session = session
        TelnetHandler.__init__(self, request, client_address, server)

    def handleException(self, exc_type, exc_param, exc_tb):
        logger.warning('Exception during telnet sessions: {0}'.format(''.join(
            traceback.format_exception(exc_type, exc_param, exc_tb))))
        return True
