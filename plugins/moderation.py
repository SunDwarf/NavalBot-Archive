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

import discord

from navalbot.api.commands import command, CommandContext
from navalbot.api.commands.cmdclass import NavalRole
from navalbot.api.util import get_user


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
        await ctx.reply("moderation.ban.low_permission", role=our_highest.name)
        return

    assert isinstance(ctx.message.server, discord.Server)

    user = get_user(ctx.message)
    if not user:
        await ctx.reply("generic.cannot_find_user", user=ctx.args[0])
        return

    if user_is_higher(user, ctx.message.server.me) or (user.id == ctx.message.server.owner_id):
        # Too high, we can't touch them.
        await ctx.reply("moderation.ban.low_permission",
                        role=our_highest.name if our_highest.name != "@everyone" else "everyone")
        return

    # Try and ban the user.
    await ctx.client.ban(ctx.message.mentions[0])
    await ctx.reply("moderation.ban.banned", target=user.display_name)
