# Copyright (C) 2018 Roman Samoilenko <ttahabatt@gmail.com>
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

import asyncio
import unittest

from heralding.reporting.reporting_relay import ReportingRelay


class BaseCapabilityTests(unittest.TestCase):
    server = None  

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(None)

        self.reporting_relay = ReportingRelay()
        self.reporting_relay_task = self.loop.run_in_executor(None, self.reporting_relay.start)

    def tearDown(self):
        self.reporting_relay.stop()
        # We give reporting_relay a chance to be finished
        self.loop.run_until_complete(self.reporting_relay_task)

        self.server.close()
        self.loop.run_until_complete(self.server.wait_closed())

        self.loop.close()

    def capability_test(self, capability_class, authfunc, options):
        capability = capability_class(options, self.loop)

        server_coro = asyncio.start_server(capability.handle_session, '127.0.0.1',
                                           8888, loop=self.loop)
        self.server = self.loop.run_until_complete(server_coro)

        if asyncio.iscoroutinefunction(authfunc):
            self.loop.run_until_complete(authfunc())
        else:
            capability_task = self.loop.run_in_executor(None, authfunc)
            self.loop.run_until_complete(capability_task)
