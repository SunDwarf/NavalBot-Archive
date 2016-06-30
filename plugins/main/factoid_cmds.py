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
from navalbot.api.contexts import CommandContext


@command("lock", argcount=1, errormsg=":x: You must provide a factoid to lock.")
async def lock(ctx: CommandContext):
    """
    Locks a factoid, so only the owner of the factoid can change it.
    """
    to_lock = ctx.args[0]
    fac = await db.get_config(ctx.message.server.id, "fac:{}".format(to_lock))
    if not fac:
        await ctx.reply("core.factoids.nonexistant", fac=to_lock)
        return
    locked = await db.get_config(ctx.message.server.id, "fac:{}:locked".format(to_lock), type_=str, default=None)
    if locked and locked != ctx.message.author.id:
        # get username
        await ctx.reply("core.factoids.cannot_edit", fac=to_lock, u=locked)
        return
    # Lock it.
    await db.set_config(ctx.message.server.id, "fac:{}:locked".format(to_lock), str(ctx.message.author.id))
    await ctx.reply("core.factoids.locked", fac=to_lock, u=ctx.message.author.id)


@command("del", "delfactoid", argcount=1, errormsg=":x: You must provide a factoid to delete.")
async def delete_factoid(ctx: CommandContext):
    """
    Deletes a factoid. It must either be unlocked or locked by you.
    """
    to_del = ctx.args[0]
    fac = await db.get_config(ctx.message.server.id, "fac:{}".format(to_del))
    if not fac:
        await ctx.reply("core.factoids.nonexistant", fac=to_del)
        return
    locked = await db.get_config(ctx.message.server.id, "fac:{}:locked".format(to_del), type_=str, default=None)
    if locked and locked != ctx.message.author.id:
        # get username
        await ctx.reply("core.factoids.cannot_edit", fac=to_del, u=locked)
        return

    # delete it
    await db.delete_config(ctx.message.server.id, "fac:{}".format(to_del))
    await db.delete_config(ctx.message.server.id, "fac:{}:locked".format(to_del))
    await ctx.reply("core.factoids.deleted", fac=to_del)


@command("unlock", argcount=1, errormsg=":x: You must provide a factoid to unlock.")
async def unlock(ctx: CommandContext):
    """
    Unlocks a factoid, so anybody can change it.
    """
    to_ulock = ctx.args[0]
    locked = await db.get_config(ctx.message.server.id, "fac:{}:locked".format(to_ulock), type_=str, default=None)
    if locked and locked != ctx.message.author.id:
        # get username
        await ctx.reply("core.factoids.cannot_edit", fac=to_ulock, u=locked)
        return
    elif not locked:
        await ctx.reply("core.factoids.nexist_or_nlock", fac=to_ulock)
        return
    await db.delete_config(ctx.message.server.id, "fac:{}:locked".format(to_ulock))
    await ctx.reply("core.factoids.unlocked", fac=to_ulock)


@command("factoids", argcount=1, errormsg=":x: You must provide a pattern to search for.")
async def factoids(ctx: CommandContext):
    """
    Searches for factoids with a specific pattern.
    """
    fac_patt = "config:{}:fac:".format(ctx.message.server.id) + ctx.args[0]
    pool = await util.get_pool()
    async with pool.get() as conn:
        assert isinstance(conn, aioredis.Redis)
        keys = conn.iscan(match=fac_patt)
    index, s = 0, ctx.locale["core.factoids.match.header"] + '\n'
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
        data = await db.get_config(ctx.message.server.id, "fac:{}".format(nkey))
        fcs.append((nkey, data))
    # Sort fcs
    fcs = sorted(fcs, key=lambda x: x[0])
    for n, k in enumerate(fcs):
        # Append to the string, using index
        s += "{}. `{}` -> `{}`\n".format(n + 1, k[0], k[1])
    if index == 0:
        s += ctx.locale["core.factoids.match.none"]
    await ctx.client.send_message(ctx.message.channel, s)
