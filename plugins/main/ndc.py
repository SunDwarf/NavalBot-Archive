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

from navalbot.api import util
from navalbot.api.botcls import NavalClient
from navalbot.api.commands import command
from navalbot.api.commands.ctx import CommandContext

getter = re.compile(r'`(?!`)(.*?)`')
multi = re.compile(r'```(.*?)```')

loop = asyncio.get_event_loop()

logger = logging.getLogger("NavalBot")


@command("reload", owner=True, argcount=1, argerr=":x: You must pick a file to reload.")
async def reload_f(ctx: CommandContext):
    """
    Reloads a module in the bot.
    """
    mod = ctx.args[0]
    if mod not in sys.modules:
        if 'plugins.' + mod not in sys.modules:
            await ctx.reply("core.ndc.not_loaded")
            return
        else:
            mod = 'cmds.' + mod
    # Reload using importlib.
    new_mod = importlib.reload(sys.modules[mod])
    # Update sys.modules
    sys.modules[mod] = new_mod
    await ctx.reply("core.ndc.reload_success")


@command("reloadall", owner=True)
async def reload_all(ctx: CommandContext):
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

    await ctx.reply("core.ndc.reload_all")


@command("py", owner=True)
async def py(ctx: CommandContext):
    match_single = getter.findall(ctx.message.content)
    match_multi = multi.findall(ctx.message.content)
    if not match_single and not match_multi:
        return
    else:
        if not match_multi:
            result = eval(match_single[0])
            await ctx.reply("```{}```".format(result))
        else:
            def r(v):
                loop.create_task(ctx.reply("```{}```".format(v)))

            exec(match_multi[0])


@command("rget", owner=True)
async def redis_get(ctx: CommandContext):
    key = getter.findall(ctx.message.content)
    if not key:
        return
    pool = await util.get_pool()
    async with pool.get() as conn:
        k = await conn.get(key[0])
        if k:
            k = k.decode()
        await ctx.reply("`{}`".format(k))


@command("plugins")
async def plugins(ctx: CommandContext):
    """
    Lists the currently loaded plugins.
    """
    mods = NavalClient.instance.modules
    s = ctx.locale["core.ndc.plugins_base"]
    plugin = ctx.locale["core.ndc.plugins"]

    for name, mod in mods.items():
        s += plugin.format(name=name, path=mod.__file__, ver=getattr(mod, "VERSION", "??"))

    await ctx.reply(s)
