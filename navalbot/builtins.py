"""
Built-in commands.

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

import re

import discord

from navalbot import factoids
from navalbot.api import db
from navalbot.api.commands import commands, command, Command
from navalbot.api.contexts import CommandContext
from navalbot.api.locale import get_locale

from navalbot import version

# Factoid matcher compiled
factoid_matcher = re.compile(r'(\S*?) is (.*)')

# Command matcher compiled
command_matcher = re.compile(r'{(.*?)}')


@command("help", argcount=1, argerror=":x: You must provide a function to check help of.")
async def help(ctx: CommandContext):
    """
    ಠ_ಠ
    """
    # Get the function
    func = commands.get(ctx.args[0])
    if not func:
        await ctx.reply("core.cfg.bad_override")
        return

    assert isinstance(func, Command)
    h = await func.help(ctx.server)

    await ctx.client.send_message(ctx.channel, h)


# region factoids
async def default(client: discord.Client, message: discord.Message):
    """
    Default command.

    Delegates to factoids.delegate().
    """
    # Create a new context.
    loc = await db.get_config(message.server.id, "lang", default=None)
    loc = get_locale(loc)

    ctx = CommandContext(client, message, loc)
    # Delegate factoids to handler to handle it.
    await factoids.delegate(ctx)
