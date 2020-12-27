import asyncio
import unittest
import socket
import ssl
import os

from heralding.capabilities import rdp
from heralding.misc.common import cancel_all_pending_tasks, generate_self_signed_cert
from heralding.reporting.reporting_relay import ReportingRelay


class RDPClient():

  @classmethod
  def ConnectionRequestPDU(cls):
    # selects tls security as highest supported method
    return b'\x03\x00\x00)$\xe0\x00\x00\x00\x00\x00Cookie: mstshash=xyz\r\n\x01\x00\x08\x00\x01\x00\x00\x00'

  @classmethod
  def ClientDataPDU(cls):
    tpkt = b'\x03\x00\x01\x8b'
    cc_header = b'\x02\xf0\x80'
    data = b'\x7fe\x82\x01\x7f\x04\x01\x01\x04\x01\x01\x01\x01\xff0\x1a\x02\x01"\x02\x01\x02\x02\x01\x00\x02\x01\x01\x02\x01\x00\x02\x01\x01\x02\x03\x00\xff\xff\x02\x01\x020\x19\x02\x01\x01\x02\x01\x01\x02\x01\x01\x02\x01\x01\x02\x01\x00\x02\x01\x01\x02\x02\x04 \x02\x01\x020 \x02\x03\x00\xff\xff\x02\x03\x00\xfc\x17\x02\x03\x00\xff\xff\x02\x01\x01\x02\x01\x00\x02\x01\x01\x02\x03\x00\xff\xff\x02\x01\x02\x04\x82\x01\x19\x00\x05\x00\x14|\x00\x01\x81\x10\x00\x08\x00\x10\x00\x01\xc0\x00Duca\x81\x02\x01\xc0\xea\x00\x04\x00\x08\x00\x00\x04\x00\x03\x01\xca\x03\xaa\t\x04\x00\x00(\n\x00\x00p\x00o\x00p\x00-\x00o\x00s\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x0c\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\xca\x01\x00\x00\x00\x00\x00\x10\x00\x07\x00!\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x06\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\xc0\x0c\x00\r\x00\x00\x00\x00\x00\x00\x00\x02\xc0\x0c\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    return tpkt + cc_header + data

  @classmethod
  def ErectDomainRequest(cls):
    tpkt = b'\x03\x00\x00\x0c'
    cc_header = b'\x02\xf0\x80'
    data = b'\x04\x01\x00\x01\x00'
    return tpkt + cc_header + data

  @classmethod
  def AttactUserRequest(cls):
    tpkt = b'\x03\x00\x00\x08'
    cc_header = b'\x02\xf0\x80'
    data = b'\x28'
    return tpkt + cc_header + data

  @classmethod
  def ChannelJoinRequest(cls, channel):
    tpkt = b'\x03\x00\x00\x0c'
    cc_header = b'\x02\xf0\x80'
    if channel == 1007:
      data = b'8\x00\x06\x03\xef'
    if channel == 1003:
      data = b'8\x00\x06\x03\xeb'
    return tpkt + cc_header + data

  @classmethod
  def ClientInfoPDU(cls):
    # This conatins credentials
    tpkt = b'\x03\x00\x01\x5f'
    cc_header = b'\x02\xf0\x80'
    data = b'd\x00\x06\x03\xebp\x81P@\x00\x00\x00\x00\x00\x00\x00\xfb\x07\t\x00\x02\x00\x08\x00\x12\x00\x00\x00\x00\x00\x00\x00\x00\x00x\x00x\x00x\x00\x00\x00\x00\x00m\x00y\x00p\x00a\x00s\x00s\x001\x002\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x16\x001\x002\x007\x00.\x000\x00.\x000\x00.\x001\x00\x00\x00\x00\x00B\x00C\x00:\x00\\\x00W\x00i\x00n\x00d\x00o\x00w\x00s\x00\\\x00S\x00y\x00s\x00t\x00e\x00m\x003\x002\x00\\\x00m\x00s\x00t\x00s\x00c\x00a\x00x\x00.\x00d\x00l\x00l\x00\x00\x00\x00\x00\xb6\xfe\xff\xffC\x00\x00\x00l\x00\x00\x00i\x00\x00\x00e\x00\x00\x00n\x00\x00\x00t\x00\x00\x00 \x00\x00\x00L\x00\x00\x00o\x00\x00\x00c\x00\x00\x00a\x00\x00\x00l\x00\x00\x00 \x00\x00\x00T\x00\x00\x00i\x00\x00\x00m\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00C\x00\x00\x00l\x00\x00\x00i\x00\x00\x00e\x00\x00\x00n\x00\x00\x00t\x00\x00\x00 \x00\x00\x00L\x00\x00\x00o\x00\x00\x00c\x00\x00\x00a\x00\x00\x00l\x00\x00\x00 \x00\x00\x00T\x00\x00\x00i\x00\x00\x00m\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x06\x00\x00\x00\x00\x00'
    return tpkt + cc_header + data

@unittest.skip("RDP is broken - see issue #144")
class RDPTests(unittest.TestCase):

  def create_cert_if_not_exists(self, pem_file):
    if not os.path.isfile(pem_file):
      cert, key = generate_self_signed_cert("US", "None", "None", "None",
                                            "None", "*", 365, 0)
      with open(pem_file, 'wb') as _pem_file:
        _pem_file.write(cert)
        _pem_file.write(key)

  def rdp_connect(self, ip_addr, port):
    s = socket.socket()
    s.connect((ip_addr, port))
    s.sendall(RDPClient.ConnectionRequestPDU())
    s.recv(1024)

    tls = ssl.wrap_socket(s, ssl_version=ssl.PROTOCOL_TLSv1_1)
    tls.sendall(RDPClient.ClientDataPDU())
    tls.recv(4096)

    tls.send(RDPClient.ErectDomainRequest())
    tls.sendall(RDPClient.AttactUserRequest())
    tls.recv(512)

    tls.sendall(RDPClient.ChannelJoinRequest(1007))
    tls.recv(1024)
    tls.sendall(RDPClient.ChannelJoinRequest(1003))
    tls.recv(1024)

    tls.sendall(RDPClient.ClientInfoPDU())
    res = b''
    res = tls.recv(512)

    if res != b'':
      return False
    return True

  def setUp(self):
    self.loop = asyncio.new_event_loop()
    asyncio.set_event_loop(None)

    self.reporting_relay = ReportingRelay()
    self.reporting_relay_task = self.loop.run_in_executor(
        None, self.reporting_relay.start)

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

    options = {
        "enabled": "True",
        "port": 3389,
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
    self.create_cert_if_not_exists('rdp.pem')
    server_coro = asyncio.start_server(
        rdp_cap.handle_session, '0.0.0.0', 8389, loop=self.loop)
    self.server = self.loop.run_until_complete(server_coro)

    rdp_task = self.loop.run_in_executor(None, rdp_login)
    login_res = self.loop.run_until_complete(rdp_task)

    self.assertEqual(True, login_res)
