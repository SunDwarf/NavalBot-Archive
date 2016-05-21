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
import shlex

import aioredis
import discord

from navalbot.api import db, decorators, util
from navalbot.api.commands import oldcommand, commands, command
from navalbot.api.commands.cmdclass import NavalRole


@oldcommand("ggetcfg")
@decorators.owner
@decorators.enforce_args(1, ":x: Config set must be in `getcfg 'key'` format, "
                            "with quotation marks surrounding the spaces")
async def g_get_config(client: discord.Client, message: discord.Message, args: list):
    """
    Globally set a config value.
    Owner-only.
    """
    val = util.get_global_config(args[0])
    await client.send_message(message.channel, "`{}` -> `{}`".format(args[0], val))


@oldcommand("set")
@oldcommand("setcfg")
@decorators.with_permission("Admin")
async def set_config(client: discord.Client, message: discord.Message):
    """
    Sets a server-specific configuration value.
    """
    # Split the content with shlex.
    split = shlex.split(message.content)
    if len(split) != 3:
        await client.send_message(message.channel, ":x: Config set must be in `setcfg 'key' 'value'` format, "
                                                   "with quotation marks surrounding the spaces")
        return
    # Get the config values
    name, val = split[1:3]
    # Set them.
    await db.set_config(message.server.id, name, val)
    await client.send_message(message.channel, ":heavy_check_mark: Config updated: `{}` -> `{}`".format(name, val))


@command("get", "getcfg", argcount=1, roles={NavalRole.ADMIN}, argerror=":x: You must provide a key to get.")
async def get_config(client: discord.Client, message: discord.Message, config_name: str):
    """
    Gets a server-specific configuration value.
    """
    # Get the value
    val = await db.get_config(message.server.id, config_name)
    await client.send_message(message.channel, "`{}` -> `{}`".format(config_name, val))


@command("avatar", argcount=1, owner=True, argerror=":x: You must provide a URL.")
async def avatar(client: discord.Client, message: discord.Message, file: str):
    """
    Changes the avatar of the bot.
    You must provide a valid url, pointing to a jpeg or png file.
    Owner-only
    """
    try:
        await util.get_file((client, message), url=file, name='avatar.jpg')
        fp = open(os.path.join(os.getcwd(), "files", "avatar.jpg"), 'rb')
        await client.edit_profile(avatar=fp.read())
        await client.send_message(message.channel, "Avatar has been changed.")
    except (ValueError, discord.errors.InvalidArgument):
        await client.send_message(message.channel, "This command only supports jpeg or png files!")


@command("name", argcount=1, owner=True, argerror=":x: You must provide a new name.")
async def changename(client: discord.Client, message: discord.Message, name: str):
    """
    Change the name of the bot.
    Owner-only
    """
    await client.edit_profile(username=name)
    await client.send_message(message.channel, 'Username got changed!')


@command("addoverride", argcount=2, roles={NavalRole.ADMIN}, argerror=":x: You must provide a command and a ")
async def add_role_override(client: discord.Client, message: discord.Message, command_name: str, role: str):
    """
    Adds a role override to a command.
    This allows anybody with the role specified to run this command.
    You can enable a command for everybody by adding a role override for `@ everybody` (without the space.).
    """
    if command_name not in commands:
        await client.send_message(message.channel, ":x: You must provide a valid command.")
        return

    # Set in aioredis
    async with (await util.get_pool()).get() as conn:
        assert isinstance(conn, aioredis.Redis)
        conn.sadd("override:{}:{}".format(message.server.id, command_name), role)

    await client.send_message(message.channel, ":x: Added role override for command {}.".format(command_name))


@command("deloverride", roles={NavalRole.ADMIN}, argcount=2, argerror=":x: You must provide a command a role.")
async def remove_role_override(client: discord.Client, message: discord.Message, args: list):
    """
    Removes a role override from a command.
    """
    command_name = args[0]
    if command_name not in commands:
        await client.send_message(message.channel, ":x: You must provide a valid command.")
        return

    role = args[1]
    # smse
    async with (await util.get_pool()).get() as conn:
        assert isinstance(conn, aioredis.Redis)
        conn.srem("override:{}:{}".format(message.server.id, command_name), role)

    await client.send_message(message.channel, ":x: Deleted role override for command {}.".format(command_name))