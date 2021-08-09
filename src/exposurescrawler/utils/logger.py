import logging
import sys
from functools import lru_cache

FORMATTER = logging.Formatter("%(asctime)s — %(name)s — %(levelname)s — %(message)s")


@lru_cache
def logger():
    _logger = logging.getLogger("exposurescrawler")
    _logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(FORMATTER)

    _logger.addHandler(console_handler)
    _logger.propagate = False

    return _logger
