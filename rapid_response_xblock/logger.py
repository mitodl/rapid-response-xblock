"""
Capture events
"""
from __future__ import absolute_import

from track.backends import BaseBackend


class LoggerBackend(BaseBackend):
    """
    Record events emitted by blocks.
    See TRACKING_BACKENDS for the configuration for this logger.
    For more information about events see:

    http://edx.readthedocs.io/projects/devdata/en/stable/internal_data_formats/tracking_logs.html
    """

    def send(self, event):
        pass
