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
import aioredis
import discord

from navalbot.api import db, util
from navalbot.api.commands import command


@command("lock", argcount=1, errormsg=":x: You must provide a factoid to lock.")
async def lock(client: discord.Client, message: discord.Message, to_lock: str):
    """
    Locks a factoid, so only the owner of the factoid can change it.
    """
    fac = await db.get_config(message.server.id, "fac:{}".format(to_lock))
    if not fac:
        await client.send_message(message.channel, ":x: Factoid `{}` does not exist".format(to_lock))
        return
    locked = await db.get_config(message.server.id, "fac:{}:locked".format(to_lock), type_=str, default=None)
    if locked and locked != message.author.id:
        # get username
        await client.send_message(message.channel, ":x: Cannot change lock, factoid is locked to ID `{}`.".format(
            locked))
        return
    # Lock it.
    await db.set_config(message.server.id, "fac:{}:locked".format(to_lock), str(message.author.id))
    await client.send_message(message.channel, ":heavy_check_mark: Factoid `{}` locked to `{}`"
                              .format(to_lock, message.author.id))


@command("del", "delfactoid", argcount=1, errormsg=":x: You must provide a factoid to delete.")
async def delete_factoid(client: discord.Client, message: discord.Message, to_del: str):
    """
    Deletes a factoid. It must either be unlocked or locked by you.
    """
    fac = await db.get_config(message.server.id, "fac:{}".format(to_del))
    if not fac:
        await client.send_message(message.channel, ":x: Factoid {} does not exist".format(to_del))
        return
    locked = await db.get_config(message.server.id, "fac:{}:locked".format(to_del), type_=str, default=None)
    if locked and locked != message.author.id:
        # get username
        await client.send_message(message.channel, ":x: Cannot delete, factoid is locked to ID `{}`.".format(locked))
        return

    # delete it
    await db.delete_config(message.server.id, "fac:{}".format(to_del))
    await db.delete_config(message.server.id, "fac:{}:locked".format(to_del))
    await client.send_message(message.channel, ":heavy_check_mark: Deleted factoid {}.".format(to_del))


@command("unlock", argcount=1, errormsg=":x: You must provide a factoid to unlock.")
async def unlock(client: discord.Client, message: discord.Message, to_ulock):
    """
    Unlocks a factoid, so anybody can change it.
    """
    locked = await db.get_config(message.server.id, "fac:{}:locked".format(to_ulock), type_=str, default=None)
    unlock_exception = discord.utils.get(message.server.roles, name='Admin')
    if locked and locked != message.author.id and not unlock_exception:
        # get username
        await client.send_message(message.channel, ":x: Cannot change lock, factoid is locked to ID `{}`.".format(
            locked))
        return
    elif not locked:
        await client.send_message(message.channel, ":x: Factoid {} does not exist/not locked.".format(to_ulock))
        return
    await db.delete_config(message.server.id, "fac:{}:locked".format(to_ulock))
    await client.send_message(message.channel, ":heavy_check_mark: Factoid `{}` unlocked.".format(to_ulock))


@command("factoids", argcount=1, errormsg=":x: You must provide a pattern to search for.")
async def factoids(client: discord.Client, message: discord.Message, fac_patt: str):
    """
    Searches for factoids with a specific pattern.
    """
    fac_patt = "config:{}:fac:".format(message.server.id) + fac_patt
    pool = await util.get_pool()
    async with pool.get() as conn:
        assert isinstance(conn, aioredis.Redis)
        keys = conn.iscan(match=fac_patt)
    index, s = 0, "Matched factoids:\n"
    fcs = []
    async for key in keys:
        # Decode it
        key = key.decode()
        if key.endswith(":locked"):
            continue
        else:
            nkey = key.split(":fac:")[1]
        if len(nkey) == 0:
            continue
        index += 1
        if index == 20:
            break
        data = await db.get_config(message.server.id, "fac:{}".format(nkey))
        fcs.append((nkey, data))
    # Sort fcs
    fcs = sorted(fcs, key=lambda x: x[0])
    for n, k in enumerate(fcs):
        # Append to the string, using index
        s += "\n{}. `{}` -> `{}`".format(n + 1, k[0], k[1])
    if index == 0:
        s += "\n`Nothing found matching that pattern.`"
    await client.send_message(message.channel, s)


@command("factoid")
async def factoid(client: discord.Client, message: discord.Message):
    """
    Displays help on how to create a factoid.
    """
    prefix = await db.get_config(message.server.id, "command_prefix", "?")
    await client.send_message(message.channel,
                              "You can create a factoid by typing `{}<factoid_name> is <answer>`".format(prefix))
