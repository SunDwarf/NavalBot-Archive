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
import os

import aioredis
import discord

from navalbot.api import db, decorators, util
from navalbot.api.commands import oldcommand, commands, command
from navalbot.api.commands.cmdclass import NavalRole
from navalbot.api.contexts import CommandContext


@command("setcfg", argcount=2, roles={NavalRole.ADMIN})
async def set_config(ctx: CommandContext):
    # Split the content with shlex.
    name, val = ctx.args[0:2]

    await db.set_config(ctx.message.server.id, name, val)

    await ctx.reply("core.cfg.setcfg_updated", name=name, val=val)


@command("getcfg", argcount=1, roles={NavalRole.ADMIN}, argerror=":x: You must provide a key to get.")
async def get_config(ctx: CommandContext):
    """
    Gets a server-specific configuration value.
    """
    # Get the value
    val = await ctx.get_config(ctx.args[0])
    await ctx.client.send_message(ctx.message.channel, "`{}` -> `{}`".format(ctx.args[0], val))


@command("delcfg", argcount=1, roles={NavalRole.ADMIN})
async def delete_config(ctx: CommandContext):
    """
    Deletes a config key
    """
    val = await ctx.get_config(ctx.args[0])
    if not val:
        await ctx.reply("core.cfg.no_such_config", name=ctx.args[0])
        return

    await ctx.delete_config(ctx.args[0])
    await ctx.reply("core.cfg.cfg_deleted", name=ctx.args[0])


@command("avatar", argcount=1, owner=True)
async def avatar(ctx: CommandContext):
    """
    Changes the avatar of the bot.
    You must provide a valid url, pointing to a jpeg or png file.
    Owner-only
    """
    try:
        await util.get_file((ctx.client, ctx.message), url=ctx.args[0], name='avatar.jpg')
        fp = open(os.path.join(os.getcwd(), "files", "avatar.jpg"), 'rb')
        await ctx.client.edit_profile(avatar=fp.read())
        await ctx.reply("core.cfg.avatar_changed")
    except (ValueError, discord.errors.InvalidArgument):
        await ctx.reply("core.cfg.avatar_invalid")


@command("name", argcount=1, owner=True, argerror=":x: You must provide a new name.")
async def changename(ctx: CommandContext):
    """
    Change the name of the bot.
    Owner-only
    """
    await ctx.client.edit_profile(username=ctx.args[0])
    await ctx.reply("core.cfg.name_changed", name=ctx.args[0])


@command("addoverride", argcount=2, roles={NavalRole.ADMIN}, argerror=":x: You must provide a command and a ")
async def add_role_override(ctx: CommandContext):
    """
    Adds a role override to a command.
    This allows anybody with the role specified to run this command.
    You can enable a command for everybody by adding a role override for `@ everybody` (without the space.).
    """
    if ctx.args[0] not in commands:
        await ctx.reply("core.cfg.bad_override")
        return

    # Set in aioredis
    async with (await util.get_pool()).get() as conn:
        assert isinstance(conn, aioredis.Redis)
        conn.sadd("override:{}:{}".format(ctx.message.server.id, ctx.args[0]), ctx.args[1])

    # await client.send_message(message.channel, ":x: Added role override for command {}.".format(command_name))
    await ctx.reply("core.cfg.added_role_override", cmd=ctx.args[0])


@command("deloverride", roles={NavalRole.ADMIN}, argcount=2, argerror=":x: You must provide a command a role.")
async def remove_role_override(ctx: CommandContext):
    """
    Removes a role override from a command.
    """
    command_name = ctx.args[0]
    if command_name not in commands:
        await ctx.reply("core.cfg.bad_override")
        return

    role = ctx.args[1]
    # smse
    async with (await util.get_pool()).get() as conn:
        assert isinstance(conn, aioredis.Redis)
        conn.srem("override:{}:{}".format(ctx.message.server.id, command_name), role)

    await ctx.reply("core.cfg_removed_role_override", cmd=command_name)
