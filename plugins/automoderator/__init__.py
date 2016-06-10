"""
Auto-moderator plugin.
"""
import os

LOCALE_DIR = os.path.join(__path__[0], "locale")

# Import automod commands
from . import cmds
