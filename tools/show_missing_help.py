"""
Small utility to show commands which are missing a help locale text.
"""

import asyncio
import time

import discord

from navalbot.api import botcls
from navalbot.api import commands

loop = asyncio.get_event_loop()

client = botcls.NavalClient()

# Load the plugins for the bot.
loop.run_until_complete(client.load_plugins())

time.sleep(0.05)

# Load the locale data.
fake_server = discord.Object(id=0)

for name, cmd in commands._func_cmd_mapping.items():
    assert isinstance(cmd, commands.Command)
    hh = loop.run_until_complete(cmd.help(fake_server))
    hh = hh.replace("\n", "")
    if hh == "This command does not have help in this language.":
        print("Missing help for:", name.__name__)