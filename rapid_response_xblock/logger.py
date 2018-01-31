"""
Capture events
"""
from __future__ import absolute_import

from track.backends import BaseBackend


class LoggerBackend(BaseBackend):
    """
    Record events
    """

    def send(self, event):
        pass
