"""
Music plugin.
"""
import os

LOCALE_DIR = os.path.join(__path__[0], "locale")
VERSION = "1.0.0"

from . import voice_main
