# Check for opus
import discord
import logging

if not discord.opus.is_loaded():
    logging.getLogger("NavalBot").error("Opus is not installed, cannot load voice module.")
else:
    # Load everything.
    pass

# Define version.
VERSION = "1.1.0"
