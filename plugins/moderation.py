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
import logging

import aioredis
import discord

from navalbot.api.commands import command
from navalbot.api.contexts import CommandContext
from navalbot.api.commands.cmdclass import NavalRole

logger = logging.getLogger("NavalBot")


def get_highest_role(user: discord.Member) -> discord.Role:
    """
    Gets the highest role that a user has.
    """
    return sorted(user.roles, key=lambda role: role.position)[-1]


def user_is_higher(user1: discord.Member, user2: discord.Member) -> bool:
    """
    Compares the two users to see which has a higher position.

    Returns True if user1's highest role is higher than user2's highest role.
    """
    u1_highest = get_highest_role(user1)
    u2_highest = get_highest_role(user2)

    return u1_highest.position > u2_highest.position


@command("ban", argcount=1, roles={NavalRole.ADMIN})
async def ban(ctx: CommandContext):
    """
    Ban a user from the server.
    """
    # Calculate our highest role
    our_highest = get_highest_role(ctx.message.server.me)

    # Check our permission.
    if not ctx.message.server.me.permissions_in(ctx.message.channel).ban_members:
        await ctx.reply("moderation.low_permission", role=our_highest.name)
        return

    assert isinstance(ctx.message.server, discord.Server)

    user = ctx.get_user()
    if not user:
        await ctx.reply("generic.cannot_find_user", user=ctx.args[0])
        return

    if user_is_higher(user, ctx.me) or (user.id == ctx.server.owner_id):
        # Too high, we can't touch them.
        await ctx.reply("moderation.low_permission",
                        role=our_highest.name if our_highest.name != "@everyone" else "everyone")
        return

    # Try and ban the user.
    await ctx.client.ban(user)
    await ctx.reply("moderation.ban.banned", target=user.display_name)


@command("kick", argcount=1, roles={NavalRole.ADMIN})
async def kick(ctx: CommandContext):
    """
    Kicks the user from the server.
    """
    our_highest = get_highest_role(ctx.me)

    if not ctx.me.permissions_in(ctx.channel).ban_members:
        await ctx.reply("moderation.low_permission", role=our_highest.name)
        return

    user = ctx.get_user()
    if not user:
        await ctx.reply("generic.cannot_find_user", user=ctx.args[0])
        return

    if user_is_higher(user, ctx.me) or (user.id == ctx.server.owner_id):
        await ctx.reply("moderation.low_permission",
                        role=our_highest.name if our_highest.name != "@everyone" else "everyone")
        return

    await ctx.client.kick(user)
    await ctx.reply("moderation.kick.kicked", target=user.display_name)


async def ensure_muted(ctx: CommandContext):
    """
    Ensures that the Muted role exists on the server, and is set to not allow speaking on all channels.
    """
    muted = discord.utils.find(lambda r: r.name == "Muted", ctx.server.roles)
    created = False
    if not muted:
        assert isinstance(ctx.server, discord.Server)
        try:
            muted = await ctx.client.create_role(ctx.server, name="Muted", permissions=discord.Permissions.none(),
                                                 colour=discord.Colour.red())
            created = True
        except discord.Forbidden:
            await ctx.reply("moderation.cannot_edit_server")
            return
        logger.info("Created new Muted role on server `{}`.".format(ctx.server.name))
    if not muted.position == 1:
        try:
            await ctx.client.move_role(ctx.server, muted, 1)
        except discord.Forbidden:
            await ctx.reply("moderation.cannot_edit_server")
            return
        logger.info("Moved Muted role to position 1 on server `{}`".format(ctx.server.name))

    if created:
        # Add `muted` denial to all channels.
        # This may seem like allowed perms, but the True means 'deny this'.
        allowed_perms = discord.Permissions.none()
        allowed_perms.send_messages = True
        allowed_perms.send_tts_messages = True
        allowed_perms.speak = True

        for chan in ctx.server.channels:
            await ctx.client.edit_channel_permissions(chan, muted, deny=allowed_perms)

    return muted


@command("mute", argcount=1, roles={NavalRole.ADMIN})
async def mute(ctx: CommandContext):
    """
    Mutes a user.
    """
    # Ensure the muted role exists.
    muted = await ensure_muted(ctx)
    if not muted:
        return
    # Locate the user.
    user = ctx.get_user()
    if not user:
        await ctx.reply("generic.cannot_find_user", user=ctx.args[0])
        return

    # Strip all their roles.
    rs = [role for role in user.roles if not role.is_everyone]
    # Save role names.
    rs_names = [r.name for r in rs]

    async with await ctx.get_conn() as conn:
        assert isinstance(conn, aioredis.Redis)
        # Add the role names to a set, with kname "muted:saved:{server_id}:{user_id}"
        sid, uid = ctx.server.id, user.id
        for rn in rs_names:
            await conn.sadd("muted:saved:{}:{}".format(sid, uid), rn)

    logger.info("Saved roles before muting user.")

    await ctx.client.remove_roles(user, *rs)

    # Add the muted role.
    await ctx.client.add_roles(user, muted)
    await ctx.reply("moderation.muted.success", user=user)


@command("unmute", argcount=1, roles={NavalRole.ADMIN})
async def unmute(ctx: CommandContext):
    """
    Unmutes a user.
    """
    muted = await ensure_muted(ctx)
    if not muted:
        return
    # Locate the user.
    user = ctx.get_user()
    if not user:
        await ctx.reply("generic.cannot_find_user", user=ctx.args[0])
        return

    if muted not in user.roles:
        await ctx.reply("moderation.muted.not_muted", user=user)
        return

    # Restore roles
    async with await ctx.get_conn() as conn:
        assert isinstance(conn, aioredis.Redis)
        sid, uid = ctx.server.id, user.id
        rns = await conn.smembers("muted:saved:{}:{}".format(sid, uid))

        to_restore = []

        # Search for the role name
        for rn in rns:
            rn = rn.decode()
            rl = discord.utils.find(lambda r: r.name == rn, ctx.server.roles)
            if not rl:
                continue
            assert isinstance(rl, discord.Role)
            to_restore.append(rl)

        # Delete the saved key.

        await ctx.client.add_roles(user, *to_restore)
        await conn.delete("muted:saved:{}:{}".format(sid, uid))

    await ctx.client.remove_roles(user, muted)
    await ctx.reply("moderation.muted.unmuted", user=user)


@command("color", "colour", argcount=1)
async def change_colour(ctx: CommandContext):
    """
    Changes your colour.
    """
    try:
        colour = int(ctx.args[0], 16)
        colour = discord.Colour(colour)
    except ValueError:
        await ctx.reply("generic.not_int", val=ctx.args[0])
        return

    # Check the role for the user.
    rl = discord.utils.get(ctx.server.roles, name="{}_colour".format(ctx.author.id))
    if not rl:
        # Create a new role.
        try:
            rl = await ctx.client.create_role(ctx.server, name="{}_colour".format(ctx.author.id),
                                              permissions=discord.Permissions.none(), colour=colour)
        except discord.Forbidden:
            await ctx.reply("moderation.cannot_edit_server")
            return
    else:
        try:
            await ctx.client.edit_role(ctx.server, rl, colour=colour)
        except discord.Forbidden:
            await ctx.reply("moderation.cannot_edit_server")
            return

    # Add it to the user, if they don't already have it.
    if rl not in ctx.author.roles:
        logger.info("Adding role {}".format(rl))
        try:
            await ctx.client.add_roles(ctx.author, rl)
        except discord.Forbidden:
            await ctx.reply("moderation.cannot_edit_server")
            return

    await ctx.reply("moderation.colour.success", c=str(colour))


@command("purge", argcount="?", roles={NavalRole.ADMIN})
async def purge(ctx: CommandContext):
    """
    Deletes messages.

    The arg is the number of messages to delete.
    """
    try:
        to_delete = int(ctx.args[0])
    except ValueError:
        to_delete = 100
    except IndexError:
        to_delete = 100

    # Create default check.
    check = lambda message: True

    # add one if applicable
    if to_delete is not None and to_delete != 100:
        to_delete += 1

    # Checks.
    if ctx.message.mentions:
        check = lambda message: message.author in ctx.message.mentions
    elif len(ctx.args) > 1:
        # Remove files.
        if ctx.args[1] == "files":
            check = lambda message: not not message.attachments

    try:
        msgs = await ctx.client.purge_from(ctx.channel, limit=to_delete, check=check)
        await ctx.reply("moderation.deleted_messages", count=len(msgs))
    except discord.Forbidden:
        await ctx.reply("moderation.cannot_edit_server")
        return


@command("clean")
async def clean(ctx: CommandContext):
    """
    Cleans bot messages.

    Removes all messages from the bot in the last 100 messages.
    """
    check = lambda msg: msg.author == ctx.me
    msgs = await ctx.client.purge_from(ctx.channel, limit=100, check=check)
    await ctx.reply("moderation.deleted_messages", count=len(msgs))


@command("blacklist", argcount=1, roles={NavalRole.ADMIN})
async def blacklist(ctx: CommandContext):
    """
    Blacklists a user, so they cannot use the bot.
    """
    user = ctx.get_user()
    if not user:
        await ctx.reply("generic.cannot_find_user", user=ctx.args[0])
        return

    # Add the item to the blacklist.
    await ctx.db.add_to_set("blacklist:{}".format(ctx.server.id), user.id)
    await ctx.reply("moderation.blacklisted", user=user.display_name)


@command("unblacklist", argcount=1, roles={NavalRole.ADMIN})
async def unblacklist(ctx: CommandContext):
    """
    Removes a user from the blacklist.
    """
    user = ctx.get_user()
    if not user:
        await ctx.reply("generic.cannot_find_user", user=ctx.args[0])
        return

    await ctx.db.remove_from_set("blacklist:{}".format(ctx.server.id), user.id)
    await ctx.reply("moderation.unblacklisted", user=user.display_name)
