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
import copy
import importlib
import inspect
import logging
import re
import sys
import traceback

import aioredis

from navalbot.api import util
from navalbot.api.botcls import NavalClient
from navalbot.api.commands import command
from navalbot.api.contexts import CommandContext

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
    # Re-load plugins.
    for mod in sys.modules:
        if mod.startswith("__"):
            continue
        if not mod.startswith("navalbot."):
            # Reload it.
            module = sys.modules[mod]
            if hasattr(module, "__file__"):
                if 'python3' in module.__file__ or 'site-packages' in module.__file__:
                    # Do not reload built-in modules
                    continue
                elif '__' in module.__file__:
                    continue
            else:
                continue
            logger.info("Reloading module: {} / {}".format(mod, module))
            importlib.reload(module)
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
            await ctx.client.send_message(ctx.message.channel, "```{}```".format(result))
        else:
            def r(v):
                loop.create_task(ctx.client.send_message(ctx.message.channel, "```{}```".format(v)))

            exec(match_multi[0])


@command("repl", owner=True)
async def repl(ctx: CommandContext):
    """
    Shameless copy of R. Danny's REPL.
    """
    loc = copy.copy(locals())
    glob = copy.copy(globals())

    await ctx.send("Inside REPL session, type `exit` or `quit` to exit.")
    while True:
        command = await ctx.client.wait_for_message(author=ctx.author, channel=ctx.channel)
        if command.content in ["exit", "quit"]:
            await ctx.send("Exiting.")
            break

        executor = exec
        if command.content.count('\n') == 0:
            # single statement, potentially 'eval'
            try:
                code = compile(command.content, '<REPL>', 'eval')
            except SyntaxError:
                pass
            else:
                executor = eval

        if executor is exec:
            try:
                code = compile(command.content, '<repl session>', 'exec')
            except SyntaxError as e:
                await ctx.send("```{}```".format(traceback.format_exc()))
                continue

        fmt = None

        try:
            result = executor(code, glob, loc)
            if inspect.isawaitable(result):
                result = await result
        except Exception as e:
            fmt = '```py\n{}\n```'.format(traceback.format_exc())
        else:
            if result is not None:
                fmt = '```py\n{}\n```'.format(result)
                loc["last"] = result

        if fmt is not None:
            if len(fmt) > 2000:
                async with ctx.client.tb_session.post("http://dpaste.com/api/v2/", data={"content": fmt}) as p:
                    await ctx.client.send_message(ctx.message.channel,
                                                  ":exclamation: Error encountered: {}".format(await p.text()))
            else:
                await ctx.send(fmt)

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
        await ctx.client.send_message(ctx.message.channel, "`{}`".format(k))


@command("rdel", owner=True)
async def redis_del(ctx: CommandContext):
    key = getter.findall(ctx.message.content)
    if not key:
        return
    pool = await util.get_pool()
    async with pool.get() as conn:
        assert isinstance(conn, aioredis.Redis)
        await conn.delete(key[0])
        await ctx.client.send_message(ctx.message.channel, "Deleted {}".format(key[0]))


@command("globalblacklist", argcount=1, owner=True)
async def globalblacklist(ctx: CommandContext):
    """
    For very naughty users.
    """
    user = ctx.get_user()
    if not user:
        # Just use the ID, if possible.
        user = None
        user_id = ctx.args[0]
    else:
        user_id = user.id

    await ctx.reply("core.ndc.globalblacklist")
    next_message = await ctx.client.wait_for_message(timeout=5, author=ctx.author, channel=ctx.channel, content="y")
    if not next_message or next_message.content != "y":
        await ctx.reply("core.ndc.globalblacklist_abort")
        return

    # Okay, you asked for it.
    await ctx.db.add_to_set("global_blacklist", user_id)
    await ctx.reply("core.ndc.globalblacklist_success", u=user_id)


@command("globalunblacklist", argcount=1, owner=True)
async def globalunblacklist(ctx: CommandContext):
    """
    When Jesus has died for your sins.
    """
    user = ctx.get_user()
    if not user:
        # Just use the ID, if possible.
        user = None
        user_id = ctx.args[0]
    else:
        user_id = user.id

    await ctx.db.remove_from_set("global_blacklist", user_id)
    await ctx.reply("core.ndc.globalunblacklist", u=user_id)


@command("plugins")
async def plugins(ctx: CommandContext):
    """
    Lists the currently loaded plugins.
    """
    mods = NavalClient._instance.modules
    s = ctx.locale["core.ndc.plugins_base"]
    plugin = ctx.locale["core.ndc.plugins"]

    for name, mod in mods.items():
        s += plugin.format(name=name)
    await ctx.client.send_message(ctx.message.channel, s)
