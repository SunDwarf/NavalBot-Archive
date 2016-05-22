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


@command("ban", argcount=1, roles={NavalRole.ADMIN})
async def ban(ctx: CommandContext):
    """
    Ban a user from the server.
    """
    # Calculate our highest role
    our_highest = sorted(ctx.message.server.me.roles, key=lambda role: role.position)[-1]

    # Check our permission.
    if not ctx.message.server.me.permissions_in(ctx.message.channel).ban_members:
        await ctx.reply("moderation.ban.low_permission", role=our_highest.name)
        return

    assert isinstance(ctx.message.server, discord.Server)

    # Check the length of the mentions
    # We must have at least one mention.
    if len(ctx.message.mentions) < 1:
        # Try and find their user.
        user = ctx.message.server.get_member_named(ctx.args[0])
        if not user:
            await ctx.reply("generic.cannot_find_user", user=ctx.args[0])
            return
        assert isinstance(user, discord.Member)
    else:
        user = ctx.message.mentions[0]
        assert isinstance(user, discord.Member)

    # Calculate their highest role.
    their_highest = sorted(user.roles, key=lambda role: role.position)[-1]
    if their_highest.position >= our_highest.position or (user.id == ctx.message.server.owner_id):
        # Too high, we can't touch them.
        await ctx.reply("moderation.ban.low_permission",
                        role=our_highest.name if our_highest.name != "@everyone" else "everyone")
        return

    # Try and ban the user.
    await ctx.client.ban(ctx.message.mentions[0])
    await ctx.reply("moderation.ban.banned", target=user.display_name)
