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
import ssl
import sys
import logging
import asyncio

import heralding.misc.common as common
import heralding.capabilities.handlerbase

from heralding.reporting.file_logger import FileLogger
from heralding.reporting.syslog_logger import SyslogLogger
from heralding.reporting.hpfeeds_logger import HpFeedsLogger

import asyncssh

from ipify import get_ip

logger = logging.getLogger(__name__)


class Honeypot:
    public_ip = ''

    def __init__(self, config, loop):
        """
        :param config: configuration dictionary.
        """
        assert config is not None
        self.loop = loop
        self.SshClass = None
        self.config = config
        self._servers = []
        self._loggers = []

    async def _record_and_lookup_public_ip(self):
        while True:
            try:
                Honeypot.public_ip = get_ip()
                logger.warning('Found public ip: {0}'.format(Honeypot.public_ip))
            except Exception as ex:
                Honeypot.public_ip = ''
                logger.warning('Could not request public ip from ipify, error: {0}'.format(ex))
            await asyncio.sleep(3600)

    def start(self):
        """ Starts services. """

        if 'public_ip_as_destination_ip' in self.config and self.config['public_ip_as_destination_ip'] is True:
            asyncio.ensure_future(self._record_and_lookup_public_ip(), loop=self.loop)

        # start activity logging
        if 'activity_logging' in self.config:
            if 'file' in self.config['activity_logging'] and self.config['activity_logging']['file']['enabled']:
                log_file = self.config['activity_logging']['file']['filename']
                file_logger = FileLogger(log_file)
                self.file_logger_task = self.loop.run_in_executor(None, file_logger.start)
                self.file_logger_task.add_done_callback(common.on_unhandled_task_exception)
                self._loggers.append(file_logger)

            if 'syslog' in self.config['activity_logging'] and self.config['activity_logging']['syslog']['enabled']:
                sys_logger = SyslogLogger()
                self.sys_logger_task = self.loop.run_in_executor(None, sys_logger.start)
                self.sys_logger_task.add_done_callback(common.on_unhandled_task_exception)
                self._loggers.append(sys_logger)

            if 'hpfeeds' in self.config['activity_logging'] and self.config['activity_logging']['hpfeeds']['enabled']:
                channel = self.config['activity_logging']['hpfeeds']['channel']
                host = self.config['activity_logging']['hpfeeds']['host']
                port = self.config['activity_logging']['hpfeeds']['port']
                ident = self.config['activity_logging']['hpfeeds']['ident']
                secret = self.config['activity_logging']['hpfeeds']['secret']
                hpfeeds_logger = HpFeedsLogger(channel, host, port, ident, secret)
                self.hpfeeds_logger_task = self.loop.run_in_executor(None, hpfeeds_logger.start)
                self.hpfeeds_logger_task.add_done_callback(common.on_unhandled_task_exception)


        for c in heralding.capabilities.handlerbase.HandlerBase.__subclasses__():
            cap_name = c.__name__.lower()
            if cap_name in self.config['capabilities']:
                if not self.config['capabilities'][cap_name]['enabled']:
                    continue
                port = self.config['capabilities'][cap_name]['port']
                # carve out the options for this specific service
                options = self.config['capabilities'][cap_name]
                # capabilities are only allowed to append to the session list
                cap = c(options, self.loop)

                try:
                    # # Convention: All capability names which end in 's' will be wrapped in ssl.
                    if cap_name.endswith('s'):
                        pem_file = '{0}.pem'.format(cap_name)
                        self.create_cert_if_not_exists(cap_name, pem_file)
                        ssl_context = self.create_ssl_context(pem_file)
                        server_coro = asyncio.start_server(cap.handle_session, '0.0.0.0', port,
                                                           loop=self.loop, ssl=ssl_context)
                    elif cap_name == 'ssh':
                        # Since dicts and user-defined classes are mutable, we have
                        # to save ssh class and ssh options somewhere.
                        ssh_options = options
                        SshClass = c
                        self.SshClass = SshClass

                        ssh_key_file = 'ssh.key'
                        SshClass.generate_ssh_key(ssh_key_file)

                        banner = ssh_options['protocol_specific_data']['banner']
                        SshClass.change_server_banner(banner)

                        server_coro = asyncssh.create_server(lambda: SshClass(ssh_options, self.loop),
                                                             '0.0.0.0', port, server_host_keys=[ssh_key_file],
                                                             login_timeout=cap.timeout, loop=self.loop)
                    else:
                        server_coro = asyncio.start_server(cap.handle_session, '0.0.0.0', port, loop=self.loop)

                    server = self.loop.run_until_complete(server_coro)
                    logger.debug('Adding {0} capability with options: {1}'.format(cap_name, options))
                    self._servers.append(server)
                except Exception as ex:
                    error_message = "Could not start {0} server on port {1}. Error: {2}".format(c.__name__, port, ex)
                    logger.error(error_message)
                    task_killer = common.cancel_all_pending_tasks(self.loop)
                    self.loop.run_until_complete(task_killer)
                    sys.exit(error_message)
                else:
                    logger.info('Started {0} capability listening on port {1}'.format(c.__name__, port))

    def stop(self):
        """Stops services"""
        if self.config['capabilities']['ssh']['enabled']:
           for conn in self.SshClass.connections_list:
               conn.close()
               self.loop.run_until_complete(conn.wait_closed())

        for server in self._servers:
            server.close()
            self.loop.run_until_complete(server.wait_closed())

        for l in self._loggers:
            l.stop()

        task_killer = common.cancel_all_pending_tasks(self.loop)
        self.loop.run_until_complete(task_killer)

        logger.info('All tasks were stopped.')

    def create_cert_if_not_exists(self, cap_name, pem_file):
        if not os.path.isfile(pem_file):
            logger.debug('Generating certificate and key: {0}'.format(pem_file))

            cert_dict = self.config['capabilities'][cap_name]['protocol_specific_data']['cert']
            cert_cn = cert_dict['common_name']
            cert_country = cert_dict['country']
            cert_state = cert_dict['state']
            cert_locality = cert_dict['locality']
            cert_org = cert_dict['organization']
            cert_org_unit = cert_dict['organizational_unit']
            valid_days = int(cert_dict['valid_days'])
            serial_number = int(cert_dict['serial_number'])

            cert, key = common.generate_self_signed_cert(cert_country, cert_state, cert_org, cert_locality,
                                                         cert_org_unit, cert_cn, valid_days, serial_number)
            with open(pem_file, 'wb') as _pem_file:
                _pem_file.write(cert)
                _pem_file.write(key)

    @staticmethod
    def create_ssl_context(pem_file):
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.check_hostname = False
        ssl_context.load_cert_chain(pem_file)
        return ssl_context
