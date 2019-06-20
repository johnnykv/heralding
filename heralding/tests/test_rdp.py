import asyncio
import unittest
import subprocess
import shlex
import os

from heralding.capabilities import rdp
from heralding.misc.common import cancel_all_pending_tasks
from heralding.reporting.reporting_relay import ReportingRelay


class RDPTests(unittest.TestCase):
    def rdp_connect(self, ip_addr, port):
        if not os.path.exists("/usr/bin/xfreerdp"):
            raise Exception("xfreeddp does't exists on the system")

        rdp_auth_fail = b'Authentication only, exit status 1'
        rdp_cmd = "/usr/bin/xfreerdp /v:%s /port:%s /u:xyz /p:testpass /cert-ignore +auth-only" % (ip_addr, port)
        prcss = subprocess.Popen(shlex.split(rdp_cmd), shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        for line in iter(prcss.stderr.readline, ''):
            if rdp_auth_fail in line:
                prcss.kill()
                prcss.wait()
                return True

        return False

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
        """Tests if rdp server responds correctly to a invalid login attempt."""

        def rdp_login():
            try:
                res = self.rdp_connect('0.0.0.0', 8389)
            except Exception as e:
                print("+++EXCEPTION+++ \n", e)
                return e
            return res

        options = {"enabled": "True", "port": 3389,
                   "protocol_specific_data": {
                       "banner": "",
                       "cert": {
                           "common_name": "*",
                           "country": "US",
                           "state": "None",
                           "locality": "None",
                           "organization": "None",
                           "organizational_unit": "None",
                           "valid_days": 365,
                           "serial_number": 0
                       }
                   }
                   }
        rdp_cap = rdp.RDP(options, self.loop)

        server_coro = asyncio.start_server(
            rdp_cap.handle_session, '0.0.0.0', 8389, loop=self.loop)
        self.server = self.loop.run_until_complete(server_coro)

        rdp_task = self.loop.run_in_executor(None, rdp_login)
        login_res = self.loop.run_until_complete(rdp_task)

        self.assertEqual(True, login_res)
