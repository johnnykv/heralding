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

from beeswarm.honeypot.consumer.loggers.loggerbase import LoggerBase

logger = logging.getLogger(__name__)


class HPFeedsLogger(LoggerBase):
    def __init__(self, config):
        super(HPFeedsLogger, self).__init__(config)
        #hpfeeds lib has problems with unicodestring - hence we encode as latin1
        host = config['log_hpfeedslogger']['host'].encode('latin1')
        port = config['log_hpfeedslogger']['port']
        secret = config['log_hpfeedslogger']['secret'].encode('latin1')
        ident = config['log_hpfeedslogger']['ident'].encode('latin1')
        self.port_mapping = eval(config['log_hpfeedslogger']['port_mapping'])
        tmpchannels = config['log_hpfeedslogger']['chan']
        if type(tmpchannels) == unicode or type(tmpchannels) == str:
            self.chan = tmpchannels.encode('latin1')
        else:
            d = []
            for chan in tmpchannels:
                d.append(chan.encode('latin1'))
            self.chan = d
        self.enabled = True
        self.hpc = hpfeeds.new(host, port, ident, secret)

    def log(self, session):
        session_dict = self.to_old_format(session)
        if session_dict['honey_port'] in self.port_mapping:
            session_dict['honey_port'] = self.port_mapping[session_dict['honey_port']]
        data = json.dumps(session_dict, default=self.json_default)
        error_msg = self.hpc.publish(self.chan, data)
        if error_msg:
            logger.warning('Error while publishing: {0}'.format(error_msg))
        return error_msg

    #to maintain compatibility with honeymap and mnemosyne we ned to convert to legacy format
    def to_old_format(self, session):

        entry = {
            'honeypot_id': session.honeypot_id,
            'id': session.id,
            'timestamp': session.timestamp,
            'attacker_ip': session.source_ip,
            'attacker_source_port': session.source_port,
            'protocol': session.protocol,
            'honey_ip': session.destination_ip,
            'honey_port': session.destination_port,
            'login_attempts': session.login_attempts,
        }

        return entry


    def json_default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, uuid.UUID):
            return str(obj)
        else:
            return None
