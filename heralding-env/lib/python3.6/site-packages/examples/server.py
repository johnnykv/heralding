import asyncio
import logging

from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Sink


async def amain(loop):
    cont = Controller(Sink(), hostname='', port=8025)
    cont.start()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    loop.create_task(amain(loop=loop))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
