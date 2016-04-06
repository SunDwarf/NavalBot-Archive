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
import shlex

import asyncio
import discord

import bot
import cmds
import util


@cmds.command("game")
async def game(client: discord.Client, message: discord.Message):
    # Set my game
    game = ' '.join(message.content.split(" ")[1:])

    if message.author.permissions_in(message.channel).manage_roles and len(game) < 64:
        # user has perms
        await client.change_status(game=discord.Game(name=game))
        await client.send_message(message.channel, "Changed game to `{}`".format(game))
        # save it in the DB
        util.cursor.execute("""INSERT OR REPLACE INTO configuration (id, name, value)
                      VALUES ((SELECT id FROM configuration WHERE name = 'game'), 'game', ?)""", (game,))
        util.db.commit()

    else:
        await client.send_message(message.channel,
                                  "You don't have the right role for this or the entered name was too long")


@cmds.command("lock")
async def lock(client: discord.Client, message: discord.Message):
    # get factoid
    fac = message.content.split(' ')[1]
    # check if it's locked
    util.cursor.execute("SELECT locked, locker FROM factoids WHERE name = ?", (fac,))
    row = util.cursor.fetchone()
    if row:
        if row[0] and row[1] != message.author.id:
            await client.send_message(message.channel, "Cannot change factoid `{}` locked by `{}`"
                                      .format(fac, row[1]))
            return
    else:
        await client.send_message(message.channel, "Factoid `{}` does not exist".format(fac))
        return
    # Update factoid to be locked
    util.cursor.execute("""UPDATE factoids SET locked = 1, locker = ? WHERE name = ?""",
                        (str(message.author.id), fac))
    util.db.commit()
    await client.send_message(message.channel, "Factoid `{}` locked to ID `{}` ({})".format(fac, message.author.id,
                                                                                            message.author.name))


@cmds.command("setcfg")
@util.with_permission("Admin")
async def set_config(client: discord.Client, message: discord.Message):
    # Split the content with shlex.
    split = shlex.split(message.content)
    if len(split) != 3:
        await client.send_message(message.channel, ":x: Config set must be in `setcfg 'key' 'value'` format, "
                                                   "with quotation marks surrounding the spaces")
        return
    # Get the config values
    name, val = split[1:3]
    # Set them.
    util.set_config(message.server.id, name, val)
    await client.send_message(message.channel, ":heavy_check_mark: Config updated: `{}` -> `{}`".format(name, val))


@cmds.command("getcfg")
@util.with_permission("Admin")
async def get_config(client: discord.Client, message: discord.Message):
    # Split the content with shlex.
    split = shlex.split(message.content)
    if len(split) != 2:
        await client.send_message(message.channel, ":x: Config set must be in `getcfg 'key'` format, "
                                                   "with quotation marks surrounding the spaces")
        return

    name = split[1]
    # Get the value
    val = util.get_config(message.server.id, name)
    await client.send_message(message.channel, "`{}` -> `{}`".format(name, val))


async def get_stdout_and_return_code(cmd: str):
    proc = await asyncio.create_subprocess_exec(*cmd.split())
    stdout, stderr = await proc.communicate()
    return stdout, stderr, proc.returncode


@cmds.command("update")
@util.only(bot.RCE_IDS)
async def update(client: discord.Client, message: discord.Message):
    await client.send_message(message.channel, "First, fetching the new data from GitHub.")
    stdout, stderr, ret = await get_stdout_and_return_code("git fetch")
    if ret != 0:
        await client.send_message(message.channel, "Command failed!\n```\nstdout:\n\n{}\nstderr:\n\n{}".format(
            stdout, stderr
        ))
        return
    await client.send_message(message.channel, "Stashing your changes.")
    stdout, stderr, ret = await get_stdout_and_return_code("git stash")
    if ret != 0:
        await client.send_message(message.channel, "Command failed!\n```\nstdout:\n\n{}\nstderr:\n\n{}".format(
            stdout, stderr
        ))
        return
    await client.send_message(message.channel, "Resetting to origin.")
    stdout, stderr, ret = await get_stdout_and_return_code("git reset origin/stable")
    if ret != 0:
        await client.send_message(message.channel, "Command failed!\n```\nstdout:\n\n{}\nstderr:\n\n{}".format(
            stdout, stderr
        ))
        return
    await client.send_message(message.channel, "Unstashing your changes.")
    stdout, stderr, ret = await get_stdout_and_return_code("git stash apply")
    if ret != 0:
        await client.send_message(message.channel, "Command failed!\n```\nstdout:\n\n{}\nstderr:\n\n{}".format(
            stdout, stderr
        ))
        return
    tdout, stderr, ret = await get_stdout_and_return_code("git rev-parse HEAD")
    await client.send_message(message.channel, "Done! Navalbot is now at revision {}.".format(tdout))