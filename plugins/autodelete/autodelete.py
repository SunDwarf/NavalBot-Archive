"""
Censorship couldn't be easier with this plugin.
"""
import logging
import re
import sre_constants

import asyncio
import discord
import functools

from navalbot.api import db
from navalbot.api.commands import command, CommandContext
from navalbot.api.commands.cmdclass import NavalRole
from navalbot.api.hooks import on_event

logger = logging.getLogger("NavalBot")


def _matches(compiled, to_check):
    """
    Simple function to check if messages match the regex.
    """
    if compiled.match(to_check):
        return True
    else:
        return False


@on_event("on_message_before_blacklist")
async def censor_hook(botcls: discord.Client, message: discord.Message):
    """
    The actual hook to run deletes.
    """

    loop = asyncio.get_event_loop()

    built = "autoremove:{}".format(message.server.id)
    res = await db.get_set(built)
    if not res:
        return
    compiled = []

    for r in res:
        compiled.append(re.compile(r))

    for comp in compiled:
        # Run the func in an executor, to prevent deadlocking the bot.
        matches = await loop.run_in_executor(None, functools.partial(_matches, comp, message.content))
        if matches:
            await botcls.delete_message(message)
            # End processing.
            return True


@command("autoremove", "autodelete", argcount="?", roles={NavalRole.ADMIN})
async def autoremove(ctx: CommandContext):
    """
    This allows you to manage automatically removing messages.
    """
    # Check for the subcommand.
    if ctx.args[0] == "add":
        await _autoremove_add(ctx)
    elif ctx.args[0] == "del":
        await _autoremove_del(ctx)
    elif ctx.args[0] == "list":
        await _autoremove_list(ctx)


async def _autoremove_add(ctx: CommandContext):
    """
    Manages autoremove adding.
    """
    if len(ctx.args) < 2:
        await ctx.reply("censor.no_args")
        return

    # Validate the regex.
    r = ' '.join(ctx.args[1:])
    try:
        re.compile(r)
    except sre_constants.error as e:
        await ctx.reply("censor.add.bad_regex", err=e)
        return

    built = "autoremove:{}".format(ctx.server.id)
    await ctx.db.add_to_set(built, r)
    await ctx.reply("censor.add.added", re=r)


async def _autoremove_list(ctx: CommandContext):
    """
    Manages autoremove listing.
    """
    built = "autoremove:{}".format(ctx.server.id)
    res = await ctx.db.get_set(built)
    if not res:
        await ctx.reply("censor.list.none")
        return

    b = ""
    for n, regex in enumerate(res):
        b += "{}. `{}`\n".format(n + 1, regex)

    await ctx.client.send_message(ctx.message.channel, b)


async def _autoremove_del(ctx: CommandContext):
    """
    Deletes an entry from autoremove.
    """
    if len(ctx.args) < 2:
        await ctx.reply("censor.no_args")
        return

    built = "autoremove:{}".format(ctx.server.id)
    res = await ctx.db.get_set(built)
    if not res:
        await ctx.reply("censor.list.none")
        return

    r = ' '.join(ctx.args[1:])
    if r in res:
        await ctx.db.remove_from_set(built, r)
        await ctx.reply("censor.del.removed", re=r)
        return

    await ctx.reply("censor.del.no_such_regex")
