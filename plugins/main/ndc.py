"""
=================================

This file is part of NavalBot.
Copyright (C) 2016 Isaac Dickinson
Copyright (C) 2016 Nils Theres

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>

=================================
"""

# Owner commands.
import asyncio
import importlib
import logging
import re
import sys

import discord

from navalbot.api import util
from navalbot.api.botcls import NavalClient
from navalbot.api.commands import command

getter = re.compile(r'`(?!`)(.*?)`')
multi = re.compile(r'```(.*?)```')

loop = asyncio.get_event_loop()

logger = logging.getLogger("NavalBot")


@command("reload", owner=True, argcount=1, argerr=":x: You must pick a file to reload.")
async def reload_f(client: discord.Client, message: discord.Message, args: list):
    """
    Reloads a module in the bot.
    """
    mod = args[0]
    if mod not in sys.modules:
        if 'plugins.' + mod not in sys.modules:
            await client.send_message(message.channel, ":x: Module is not loaded.")
            return
        else:
            mod = 'cmds.' + mod
    # Reload using importlib.
    new_mod = importlib.reload(sys.modules[mod])
    # Update sys.modules
    sys.modules[mod] = new_mod
    await client.send_message(message.channel, ":heavy_check_mark: Reloaded module.")


@command("reloadall", owner=True)
async def reload_all(client: discord.Client, message: discord.Message):
    """
    Reloads all modules.
    """
    # Reload all navalbot stuff FIRST
    for mod in sys.modules:
        if mod.startswith("navalbot."):
            # Reload it.
            logger.info("Reloading module: {}".format(mod))
            importlib.reload(sys.modules[mod])
            logger.info("Reloaded module.")

    # Then re-load plugins.
    for mod in sys.modules:
        if mod.startswith("plugins."):
            # Reload it.
            logger.info("Reloading module: {}".format(mod))
            importlib.reload(sys.modules[mod])
            logger.info("Reloaded module.")

    await client.send_message(message.channel, ":heavy_check_mark: Reloaded all.")


@command("py", owner=True)
async def py(client: discord.Client, message: discord.Message):
    match_single = getter.findall(message.content)
    match_multi = multi.findall(message.content)
    if not match_single and not match_multi:
        return
    else:
        if not match_multi:
            result = eval(match_single[0])
            await client.send_message(message.channel, "```{}```".format(result))
        else:
            def r(v):
                loop.create_task(client.send_message(message.channel, "```{}```".format(v)))

            exec(match_multi[0])


@command("rget", owner=True)
async def redis_get(client: discord.Client, message: discord.Message):
    key = getter.findall(message.content)
    if not key:
        return
    pool = await util.get_pool()
    async with pool.get() as conn:
        k = await conn.get(key[0])
        if k:
            k = k.decode()
        await client.send_message(message.channel, "`{}`".format(k))


@command("plugins")
async def plugins(client: discord.Client, message: discord.Message):
    """
    Lists the currently loaded plugins.
    """
    mods = NavalClient.instance.modules
    s = "**Currently loaded plugins:**"
    for name, mod in mods.items():
        s += "\n`{} (from {})` - version **{}**".format(name, mod.__file__, getattr(mod, "VERSION", "??"))
    await client.send_message(message.channel, s)
