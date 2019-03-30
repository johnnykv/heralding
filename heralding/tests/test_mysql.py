import asyncio
import unittest

import pymysql
from heralding.capabilities import mysql
from heralding.misc.common import cancel_all_pending_tasks
from heralding.reporting.reporting_relay import ReportingRelay


class MySQLTests(unittest.TestCase):
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
        """Tests if mysql server responds correctly to a invalid login attempt."""

        def mysql_login():
            try:
                pymysql.connect(host="0.0.0.0",
                                port=8306,
                                user="tuser",
                                password="tpass",
                                db="testdb")
            except pymysql.err.OperationalError as e:
                return e
            return None

        options = {'enabled': 'True', 'port': 8306}
        mysql_cap = mysql.MySQL(options, self.loop)

        server_coro = asyncio.start_server(
            mysql_cap.handle_session, '0.0.0.0', 8306, loop=self.loop)
        self.server = self.loop.run_until_complete(server_coro)

        mysql_task = self.loop.run_in_executor(None, mysql_login)
        login_exception = self.loop.run_until_complete(mysql_task)

        self.assertIsInstance(login_exception, pymysql.err.OperationalError)
        self.assertEqual(
            str(login_exception),
            '(1045, "Access denied for user \'tuser\'@\'127.0.0.1\' (using password: YES)")'
        )

    def cb(self, socket, command, option):
        return
