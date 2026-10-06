import logging
import os
import sys

logger = logging.getLogger("payments")
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(module)s] %(message)s"))
logger.addHandler(_handler)
logger.propagate = False
