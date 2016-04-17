import logging
import os
import time
import sys
logger = logging.getLogger(__name__)


def on_unhandled_greenlet_exception(dead_greenlet):
    logger.error('Stopping because %s died: %s', dead_greenlet, dead_greenlet.exception)
    sys.exit(1)
