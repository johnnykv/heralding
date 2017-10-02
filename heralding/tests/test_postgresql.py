import asyncio
import unittest

import psycopg2
from heralding.capabilities import postgresql
from heralding.misc.common import cancel_all_pending_tasks
from heralding.reporting.reporting_relay import ReportingRelay


class PostgreSQLTests(unittest.TestCase):
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

        self.loop.run_until_complete(cancel_all_pending_tasks(self.loop))
        self.loop.close()

    def test_invalid_login(self):
        """Tests if postgres server responds correctly to a invalid login attempt."""

        def postgresql_login():
            try:
                psycopg2.connect("postgres://scott:tiger@0.0.0.0:2504/")
            except psycopg2.OperationalError as e:
                return e
            return None

        options = {'enabled': 'True', 'port': 2504}
        postgresql_cap = postgresql.PostgreSQL(options, self.loop)

        server_coro = asyncio.start_server(
            postgresql_cap.handle_session, '0.0.0.0', 2504, loop=self.loop)
        self.server = self.loop.run_until_complete(server_coro)

        postgresql_task = self.loop.run_in_executor(None, postgresql_login)
        login_exception = self.loop.run_until_complete(postgresql_task)

        self.assertIsInstance(login_exception, psycopg2.OperationalError)
        self.assertEqual(
            str(login_exception),
            'FATAL:  password authentication failed for user "scott"\n'
        )

    def cb(self, socket, command, option):
        return
