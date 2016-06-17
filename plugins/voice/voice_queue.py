"""
=================================

This file is part of NavalBot.
Copyright (C) 2016 Isaac Dickinson

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

from navalbot.api.commands import command
from navalbot.api.commands.cmdclass import NavalRole
from navalbot.api.contexts import CommandContext
from navalbot.voice.voice_util import author_is_valid, find_voice_channel
from .stores import voice_params


@command("again")
async def again(ctx: CommandContext):
    """
    Adds this item to the queue again.
    """
    vc = ctx.client.voice_client_in(ctx.message.server)
    if not vc:
        await ctx.reply("voice.not_connected")
        return

    channels = [vc.channel, find_voice_channel(ctx.message.server), ctx.message.author.voice_channel]

    if not author_is_valid(ctx.message.author, channels):
        await ctx.reply("voice.cant_control")
        return

    await vc.cmd_again(ctx)


@command("shuffle", roles={NavalRole.VOICE, NavalRole.ADMIN, NavalRole.BOT_COMMANDER})
async def shuffle(ctx: CommandContext):
    """
    Shuffles the queue.
    """
    vc = ctx.client.voice_client_in(ctx.message.server)
    if not vc:
        await ctx.reply("voice.not_connected")
        return

    channels = [vc.channel, find_voice_channel(ctx.message.server), ctx.message.author.voice_channel]

    if not author_is_valid(ctx.message.author, channels):
        await ctx.reply("voice.cant_control")
        return

    await vc.cmd_shuffle(ctx)


@command("queue", "queued")
async def get_queued_vids(ctx: CommandContext):
    """
    Get the current playback queue for this server.
    """
    # STILL HORRIBLE
    try:
        start_pos = int(ctx.message.content.split(" ")[1])
    except (ValueError, IndexError):
        start_pos = 0

    vc = ctx.client.voice_client_in(ctx.message.server)
    if not vc:
        await ctx.reply("voice.not_connected")
        return

    await vc.cmd_queue(ctx, start_pos)


@command("stop", "skip", roles={NavalRole.ADMIN, NavalRole.BOT_COMMANDER, NavalRole.VOICE})
async def skip(ctx: CommandContext):
    """
    Skips ahead one or more tracks.
    """

    vc = ctx.client.voice_client_in(ctx.message.server)
    if not vc:
        await ctx.reply("voice.not_connected")
        return

    channels = [vc.channel, find_voice_channel(ctx.message.server), ctx.message.author.voice_channel]

    if not author_is_valid(ctx.message.author, channels):
        await ctx.reply("voice.cant_control")
        return

    try:
        aaa = ctx.message.content.split(" ")
        if aaa[1] == "all":
            to_skip = 9999999
        else:
            to_skip = int(aaa[1])

    except IndexError:
        to_skip = 1
    except ValueError:
        to_skip = 1

    # Await cmd_skip
    await vc.cmd_skip(ctx, to_skip)


@command("voteskip")
async def voteskip(ctx: CommandContext):
    """
    Starts a vote to skip the currently playing track.
    """
    vc = ctx.client.voice_client_in(ctx.message.server)
    if not vc:
        await ctx.reply("voice.not_connected")
        return

    channels = [vc.channel, find_voice_channel(ctx.message.server), ctx.message.author.voice_channel]

    if not author_is_valid(ctx.message.author, channels):
        await ctx.reply("voice.cant_control")
        return

    await vc.cmd_voteskip(ctx, ctx.message.author.id)


@command("move", argcount=2, argerror=":x: You must provide two numbers: The original position, and the new position.")
async def move(ctx: CommandContext):
    """
    Moves a song in the queue from position <x> to position <y>.

    Both numbers must be integers.
    """
    vc = ctx.client.voice_client_in(ctx.message.server)
    if not vc:
        await ctx.reply("voice.not_connected")
        return

    channels = [vc.channel, find_voice_channel(ctx.message.server), ctx.message.author.voice_channel]

    if not author_is_valid(ctx.message.author, channels):
        await ctx.reply("voice.cant_control")
        return

    try:
        fr = int(ctx.args[0])
        to = int(ctx.args[1])
    except ValueError:
        await ctx.reply("generic.not_int", val=ctx.args[0])
        return

    fr, to = fr - 1, to - 1

    await vc.cmd_move(ctx, fr, to)


@command("remove", roles={NavalRole.ADMIN, NavalRole.BOT_COMMANDER, NavalRole.VOICE},
         argcount="?", argerror=":x: You must give an index to remove.")
async def remove_vid(ctx: CommandContext):
    """
    Removes a video at a specific index from the queue.
    """
    vc = ctx.client.voice_client_in(ctx.message.server)
    if not vc:
        await ctx.reply("voice.not_connected")
        return

    channels = [vc.channel, find_voice_channel(ctx.message.server), ctx.message.author.voice_channel]

    if not author_is_valid(ctx.message.author, channels):
        await ctx.reply("voice.cant_control")
        return

    if len(ctx.args) == 2:
        try:
            fr = int(ctx.args[0])
            end = int(ctx.args[1])
        except ValueError as e:
            fr, end = 0, 1
    else:
        try:
            fr = int(ctx.args[0])
            end = None
        except ValueError as e:
            fr, end = 0, 1

    # Call cmd_remove
    await vc.cmd_remove(ctx, fr, end)
