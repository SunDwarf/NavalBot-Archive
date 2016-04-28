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
import asyncio
import os
import shlex

import db
import discord

import cmds
import util

@cmds.command("ggetcfg")
@util.owner
@util.enforce_args(1, ":x: Config set must be in `getcfg 'key'` format, "
                      "with quotation marks surrounding the spaces")
async def g_get_config(client: discord.Client, message: discord.Message, args: list):
    """
    Globally set a config value.
    Owner-only.
    """
    val = util.get_global_config(args[0])
    await client.send_message(message.channel, "`{}` -> `{}`".format(args[0], val))


@cmds.command("set")
@cmds.command("setcfg")
@util.with_permission("Admin")
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


@cmds.command("get")
@cmds.command("getcfg")
@util.with_permission("Admin")
async def get_config(client: discord.Client, message: discord.Message):
    """
    Gets a server-specific configuration value.
    """
    # Split the content with shlex.
    split = shlex.split(message.content)
    if len(split) != 2:
        await client.send_message(message.channel, ":x: Config set must be in `getcfg 'key'` format, "
                                                   "with quotation marks surrounding the spaces")
        return

    name = split[1]
    # Get the value
    val = await db.get_config(message.server.id, name)
    await client.send_message(message.channel, "`{}` -> `{}`".format(name, val))


async def get_stdout_and_return_code(cmd: str):
    proc = await asyncio.create_subprocess_exec(*cmd.split(), stdout=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    returncode = await proc.wait()
    return stdout, stderr, returncode


@cmds.command("avatar")
@util.owner
@util.enforce_args(1, error_msg='You need to provide a link')
async def avatar(client: discord.Client, message: discord.Message, args: list):
    """
    Changes the avatar of the bot.
    You must provide a valid url, pointing to a jpeg or png file.
    Owner-only
    """
    file = args[0]
    try:
        await util.get_file((client, message), url=file, name='avatar.jpg')
        fp = open(os.path.join(os.getcwd(), "files", "avatar.jpg"), 'rb')
        await client.edit_profile(avatar=fp.read())
        await client.send_message(message.channel, "Avatar got changed!")
    except (ValueError, discord.errors.InvalidArgument):
        await client.send_message(message.channel, "This command only supports jpeg or png files!")


@cmds.command("changename")
@util.owner
@util.enforce_args(1, error_msg="You need to provide the new name")
async def changename(client: discord.Client, message: discord.Message, args: list):
    """
    Change the name of the bot.
    Owner-only
    """
    name = args[0]
    await client.edit_profile(username=name)
    await client.send_message(message.channel, 'Username got changed!')
