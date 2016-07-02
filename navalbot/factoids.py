"""
Factoid stuff.

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
import hashlib
import os
import random
import re
import shlex
import string

import discord

from navalbot.api.commands import commands
from navalbot.api.contexts import CommandContext
# Factoid matcher compiled
from navalbot.api.util import sanitize, get_file, get_image, logger

factoid_matcher = re.compile(r'(.*?) is (.*)', re.S)

# Command matcher compiled
command_matcher = re.compile(r'{(.*)}')


async def delegate(ctx: CommandContext):
    """
    Factoid delegate handler.
    """
    prefix = await ctx.get_config("command_prefix", "?")
    data = ctx.message.content[len(prefix):]
    # Match it.
    matches = factoid_matcher.match(data)
    if matches:
        await set_factoid(ctx, matches)
    else:
        await get_factoid(ctx, data)


async def set_factoid(ctx: CommandContext, match):
    """
    Sets a new factoid.

    Parses commands as appropriate.
    """
    name = match.groups()[0]
    fac = match.groups()[1]
    if not (len(name) > 0 and len(fac) > 0):
        return
    # Check if it's locked.
    locked = await ctx.get_config("factoid:{}:locked".format(name))
    if locked and locked != ctx.author.id:
        await ctx.reply("core.factoids.cannot_edit", fac=name, u=locked)
        return

    # Download the factoid, if applicable.
    if fac.startswith("http") and 'youtube' not in fac:
        # download the file, with a filename.
        fname = await get_image(url=fac)
        if fname:
            fac = "file:{}".format(fname)

    await ctx.set_config("fac:{}".format(name), fac)
    await ctx.reply("core.factoids.set", name=name, content=fac)


async def get_factoid(ctx: CommandContext, data: str):
    """
    Loads a factoid from the DB.
    """
    prefix = await ctx.get_config("command_prefix", "?")
    # Split data apart and load that factoid, because fuck spaces.
    # Try data.split(" ")[0]
    ff = data.split(" ")[0]
    content = await ctx.get_config("fac:{}".format(ff))
    if not content:
        # Don't do anything.
        content = await ctx.get_config("fac:{}".format(data))
        if not content:
            return

    # Check if it is an inline command.
    inline_cmd = command_matcher.match(content)
    if inline_cmd:
        # It matches, so extract out everything.
        grp = inline_cmd.groups()
        # Load the command word, and check it.
        data = grp[0]
        command_word = grp[0].split(" ")[0]

        if command_word.startswith(prefix):
            command_word = command_word[len(prefix):]

        # Check if it is in commands.
        if command_word not in commands:
            await ctx.reply("generic.cannot_find_command", cmd=command_word)
            return

        # Load out the command.

        # Load up the old arguments and content
        old_content = ctx.message.content
        try:
            old_args = shlex.split(old_content[len(prefix):])[1:]
        except ValueError:
            old_args = old_content[len(prefix):].split(" ")[1:]

        if not ('{' in content and '}' in content):
            # Just replace the data with the factoid data, instead of parsing out args.
            ctx.message.content = prefix + data
        else:
            # Format the new content, using the inline command args.
            try:
                ctx.message.content = prefix + data.format(*old_args, full=' '.join(old_args))
            except ValueError:
                await ctx.reply("core.factoids.bad_args")

        # Re-calculate mentions.
        user_ids = ctx.message.raw_mentions
        ctx.message.mentions = []
        for id in user_ids:
            user = ctx.message.server.get_member(id)
            if not user:
                # User left since factoid was made.
                continue
            ctx.message.mentions.append(user)

        ctx.message.channel_mentions = []
        for id in ctx.message.raw_channel_mentions:
            chan = ctx.message.server.get_channel(id)
            if not chan:
                continue
            ctx.message.channel_mentions.append(chan)

        ctx.message.role_mentions = []
        for id in ctx.message.raw_role_mentions:
            role = discord.utils.get(ctx.message.server.roles, id=id)
            if not role:
                continue
            ctx.message.role_mentions = []

        # Invoke the new function.
        command = commands[command_word]
        logger.info("Invoking factoid command `{}` with args `{}`".format(command_word, ctx.message.content))
        await command.invoke(ctx)
        return

    # Check if it's a file.
    if content.startswith("file:"):
        fname = content.lstrip("file:")
        # Sanitize the filename, to be safe.
        fname = sanitize(fname)
        # Open and send the file.
        if not os.path.exists(os.path.join(os.getcwd(), 'files', fname)):
            return
        with open(os.path.join(os.getcwd(), 'files', fname), 'rb') as f:
            await ctx.client.send_file(ctx.channel, f)
            return

    # Otherwise, just send the content.
    await ctx.client.send_message(ctx.channel, content)
