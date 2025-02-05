"""VeSync API Library."""

# pylint: skip-file
# flake8: noqa
from .vesync import VeSync
import logging

__version__ = '2.2.0'

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(levelname)5s - %(message)s'
)
