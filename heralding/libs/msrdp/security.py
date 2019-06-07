#
# Copyright (c) 2014-2015 Sylvain Peyrefitte
#
# This file is part of rdpy.
#
# rdpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import rsa
import hashlib
from . import rc4_dec as rc4
from .rc4 import RC4


def saltedHash(inputData, salt, salt1, salt2):
    """
    @summary: Generate particular signature from combination of sha1 and md5
    @see: http://msdn.microsoft.com/en-us/library/cc241992.aspx
    @param inputData: strange input (see doc)
    @param salt: salt for context call
    @param salt1: another salt (ex : client random)
    @param salt2: another another salt (ex: server random)
    @return : MD5(Salt + SHA1(Input + Salt + Salt1 + Salt2))
    """
    sha1Digest = hashlib.sha1()
    md5Digest = hashlib.md5()

    sha1Digest.update(inputData)
    sha1Digest.update(salt[:48])
    sha1Digest.update(salt1)
    sha1Digest.update(salt2)
    sha1Sig = sha1Digest.digest()

    md5Digest.update(salt[:48])
    md5Digest.update(sha1Sig)

    return md5Digest.digest()


def finalHash(key, random1, random2):
    """
    @summary: MD5(in0[:16] + in1[:32] + in2[:32])
    @param key: in 16
    @param random1: in 32
    @param random2: in 32
    @return MD5(in0[:16] + in1[:32] + in2[:32])
    """
    md5Digest = hashlib.md5()
    md5Digest.update(key)
    md5Digest.update(random1)
    md5Digest.update(random2)
    return md5Digest.digest()


def masterSecret(secret, random1, random2):
    """
    @summary: Generate master secret
    @param secret: {str} secret
    @param clientRandom : {str} client random
    @param serverRandom : {str} server random
    @see: http://msdn.microsoft.com/en-us/library/cc241992.aspx
    """
    return saltedHash(b"A", secret, random1, random2) + saltedHash(b"BB", secret, random1, random2) + saltedHash(b"CCC", secret, random1, random2)


def sessionKeyBlob(secret, random1, random2):
    """
    @summary: Generate master secret
    @param secret: secret
    @param clientRandom : client random
    @param serverRandom : server random
    """
    return saltedHash(b"X", secret, random1, random2) + saltedHash(b"YY", secret, random1, random2) + saltedHash(b"ZZZ", secret, random1, random2)


def generateRC4Keys(clientRandom, serverRandom):
    """
    @param method: removed as 128bit is deafult
    @param clientRandom: {str[32]} client random
    @param serverRandom: {str[32]} server random
    @see: http://msdn.microsoft.com/en-us/library/cc240785.aspx
    @return: MACKey, initialFirstKey128(ClientdecryptKey, serverEncryptKey), initialSecondKey128(ServerDecryptKey, ClientEncryptKey)
    """
    preMasterHash = clientRandom[:24] + serverRandom[:24]
    masterHash = masterSecret(preMasterHash, clientRandom, serverRandom)
    sessionKey = sessionKeyBlob(masterHash, clientRandom, serverRandom)
    macKey128 = sessionKey[:16]
    initialFirstKey128 = finalHash(sessionKey[16:32], clientRandom, serverRandom)
    initialSecondKey128 = finalHash(sessionKey[32:48], clientRandom, serverRandom)

    # only 128bit key generated as it was set default in ServerSecurityDataPDU
    return macKey128, initialFirstKey128, initialSecondKey128


def generateRSAKeys():
    """Generates new 512-Bit RSA keys"""
    return rsa.newkeys(512)


# def PublicKey(e, n):
#     """
#     @param e: {long | str}public exponent
#     @param n: {long | str}modulus
#     """
#     if isinstance(e, bytes):
#         e = rsa.transform.bytes2int(e)
#     if isinstance(n, bytes):
#         n = rsa.transform.bytes2int(n)
#     return {'e': e, 'n': n}


def PrivateKey(d, n):
    """
    @param d: {long | str}private exponent
    @param n: {long | str}modulus
    """
    if isinstance(d, bytes):
        d = rsa.transform.bytes2int(d)
    if isinstance(n, bytes):
        n = rsa.transform.bytes2int(n)
    return {'d': d, 'n': n}


def int2bytes(i, fill_size=None):
    """wrapper of rsa.transform.int2bytes"""
    return rsa.transform.int2bytes(i, fill_size)


def signRSA(message, privateKey):
    """
    @summary: sign message with private key
    @param message: {str} message to sign
    @param privateKey : {rsa.privateKey} key use to sugn
    """
    return rsa.transform.int2bytes(rsa.core.encrypt_int(rsa.transform.bytes2int(message), privateKey['d'], privateKey['n']), rsa.common.byte_size(privateKey['n']))


def decryptRSA(message, privateKey):
    """
    @summary: wrapper around rsa.core.decrypt_int function
    @param message: {str} source message
    @param publicKey: {rsa.PrivateKey}
    """
    return rsa.transform.int2bytes(rsa.core.decrypt_int(rsa.transform.bytes2int(message), privateKey['d'], privateKey['n']))


class ServerSecurity():
    # http://msdn.microsoft.com/en-us/library/cc240776.aspx
    _TERMINAL_SERVICES_MODULUS_ = b"\x3d\x3a\x5e\xbd\x72\x43\x3e\xc9\x4d\xbb\xc1\x1e\x4a\xba\x5f\xcb\x3e\x88\x20\x87\xef\xf5\xc1\xe2\xd7\xb7\x6b\x9a\xf2\x52\x45\x95\xce\x63\x65\x6b\x58\x3a\xfe\xef\x7c\xe7\xbf\xfe\x3d\xf6\x5c\x7d\x6c\x5e\x06\x09\x1a\xf5\x61\xbb\x20\x93\x09\x5f\x05\x6d\xea\x87"
    _TERMINAL_SERVICES_PRIVATE_EXPONENT_ = b"\x87\xa7\x19\x32\xda\x11\x87\x55\x58\x00\x16\x16\x25\x65\x68\xf8\x24\x3e\xe6\xfa\xe9\x67\x49\x94\xcf\x92\xcc\x33\x99\xe8\x08\x60\x17\x9a\x12\x9f\x24\xdd\xb1\x24\x99\xc7\x3a\xb8\x0a\x7b\x0d\xdd\x35\x07\x79\x17\x0b\x51\x9b\xb3\xc7\x10\x01\x13\xe7\x3f\xf3\x5f"
    _TERMINAL_SERVICES_PUBLIC_EXPONENT_ = b"\x5b\x7b\x88\xc0"

    SERVER_RANDOM = b'\xf9\xdf\xc4p\x8a\x08\xcds5Q:\xa3!_\x8f\xa1\xeeQ\xd6Nj\x95Zy0\x12\xbf\xf5&\xfb!('
    SERVER_PUBKEY_PROPS_1 = b'\x01\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x06\x00\x5c\x00'
    SERVER_PUBKEY_PROPS_2 = b'RSA1H\x00\x00\x00\x00\x02\x00\x00?\x00\x00\x00'
    PADDING = b'\x00\x00\x00\x00\x00\x00\x00\x00'
    SERVER_PUBLIC_EXPONENT = b'\x01\x00\x01\x00'
    # SERVER_MODULUS = b'g3\x9c\xd5\x94\xa0\tO\xbfrVt`\xab\x7f\xf1+\xf7J\x86\xa3(ZK\x12\xc44(\xcd\xec"E6a\xf3\x1d&\t\x8fL\xb6\xc8f\x9c\xd0\xa3\xaf8\xaa\xe1\xfb\xcb\\\r\xfc\xbb\xd8\x93\x1cZ\xce\x1b\x8f\x92\x00\x00\x00\x00\x00\x00\x00\x00'

    def __init__(self):
        self._pubKey, self._privKey = generateRSAKeys()
        self._modulusBytes = int2bytes(self._pubKey.n)
        # self._exponentBytes = int2bytes(self._pubKey.e)
        self._exponentBytes = ServerSecurity.SERVER_PUBLIC_EXPONENT
        self._clientRandom = None # set it

    def getSignatureHash(self):
        # this is a signature of first 6 fields in ServerCert
        DATA = ServerSecurity.SERVER_PUBKEY_PROPS_1+ServerSecurity.SERVER_PUBKEY_PROPS_2 + \
            self._exponentBytes+self._modulusBytes+ServerSecurity.PADDING

        md5Digest = hashlib.md5()
        md5Digest.update(DATA)
        return md5Digest.digest() + b"\x00" + b"\xff" * 45 + b"\x01"

    def getServerCertBytes(self):
        sigHash = signRSA(self.getSignatureHash()[::-1], PrivateKey(d=ServerSecurity._TERMINAL_SERVICES_PRIVATE_EXPONENT_[
                          ::-1], n=ServerSecurity._TERMINAL_SERVICES_MODULUS_[::-1]))[::-1]
        sigBlobProps = b'\x08\x00\x48\x00'
        return ServerSecurity.SERVER_PUBKEY_PROPS_1+ServerSecurity.SERVER_PUBKEY_PROPS_2 + \
            self._exponentBytes+self._modulusBytes+ServerSecurity.PADDING+sigBlobProps+sigHash+ServerSecurity.PADDING

    def decryptClientRandom(self, encRandom):
        self._decClientRandom = decryptRSA(encRandom[::-1], self._privKey)[::-1]
        return self._decClientRandom

    def decryptClientInfo(self, encInfo):
        self._macKey, self._encKey, self._decKey = generateRC4Keys(self._decClientRandom, ServerSecurity.SERVER_RANDOM)
        self._decryptRc4 = rc4.RC4Key(self._decKey)
        decrypted = rc4.crypt(self._decryptRc4, encInfo)
        # decrypted = RC4(self._decKey).crypt(encInfo)
        return decrypted
