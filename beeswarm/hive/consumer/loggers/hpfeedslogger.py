# Copyright (C) 2013 Johnny Vestergaard <jkv@unixcluster.dk>
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

import logging
import json
import uuid
from datetime import datetime
import hpfeeds

from beeswarm.hive.consumer.loggers.loggerbase import LoggerBase

logger = logging.getLogger(__name__)


class HPFeedsLogger(LoggerBase):

    def __init__(self, config):
        super(HPFeedsLogger, self).__init__(config)
        host = config['log_hpfeedslogger']['host'].encode('latin1')
        port = config['log_hpfeedslogger']['port']
        secret = config['log_hpfeedslogger']['secret'].encode('latin1')
        ident = config['log_hpfeedslogger']['ident'].encode('latin1')
        self.port_mapping = eval(config['log_hpfeedslogger']['port_mapping'])
        self.chan = config['log_hpfeedslogger']['chan']
        self.enabled = True
        self.hpc = hpfeeds.new(host, port, ident, secret)

    def log(self, session):
        session_dict = session.to_dict()
        if session_dict['honey_port'] in self.port_mapping:
            session_dict['honey_port'] = self.port_mapping[session_dict['honey_port']]
        data = json.dumps(session_dict, default=self.json_default)
        error_msg = self.hpc.publish(self.chan, data)
        if error_msg:
            logger.warning('Error while publishing: {0}'.format(error_msg))
        return error_msg

    def json_default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, uuid.UUID):
            return str(obj)
        else:
            return None
