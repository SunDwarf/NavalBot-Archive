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

import asyncio
import random
from math import trunc, ceil

import discord

from navalbot.api.commands import oldcommand, command
from navalbot.api import db
from navalbot.voice.voice_util import author_is_valid, find_voice_channel
from navalbot.voice.voiceclient import NavalVoiceClient
from .stores import voice_params


@command("again")
async def again(client: discord.Client, message: discord.Message):
    """
    Adds this item to the queue again.
    """
    if message.server.id not in voice_params:
        await client.send_message(message.channel, content=":x: Not currently connected on this server.")
        return

    # Get the item from the queue.
    i = voice_params[message.server.id].get("curr_coro")
    if not i:
        await client.send_message(message.channel, content=":x: Nothing to play again.")
        return

    # Add it to the queue.
    try:
        queue = voice_params[message.server.id]["queue"]
        title = voice_params[message.server.id]["title"]
        assert isinstance(queue, asyncio.Queue)
        queue.put_nowait((i, title))
    except KeyError:
        await client.send_message(message.channel, content=":x: No queue to place item on.")
    except asyncio.QueueFull:
        await client.send_message(message.channel, content=":x: Queue is full.")
    else:
        await client.send_message(message.channel, content=":heavy_check_mark: Repeating track.")


@command("shuffle", roles={"Admin", "Bot Commander", "Voice"})
async def shuffle(client: discord.Client, message: discord.Message):
    """
    Shuffles the queue.
    """
    vc = client.voice_client_in(message.server)
    if not vc:
        await client.send_message(message.channel, ":x: Not currently connected on this server.")
        return

    channels = [vc.channel, find_voice_channel(message.server), message.author.voice_channel]

    if not author_is_valid(message.author, channels):
        await client.send_message(message.channel, ":x: You must be in voice and not deafened to control me.")
        return

    s = await vc.cmd_shuffle()

    await client.send_message(message.channel, s)


@command("queue", "queued")
async def get_queued_vids(client: discord.Client, message: discord.Message):
    """
    Get the current playback queue for this server.
    """
    # STILL HORRIBLE
    try:
        start_pos = int(message.content.split(" ")[1])
    except (ValueError, IndexError):
        start_pos = 0

    vc = client.voice_client_in(message.server)
    if not vc:
        await client.send_message(message.channel, ":x: Not currently connected on this server.")
        return

    # Get the queue text.
    s = await vc.cmd_queue(start_pos)

    await client.send_message(message.channel, s)


@command("skip", roles={"Admin", "Bot Commander", "Voice"})
async def skip(client: discord.Client, message: discord.Message):
    """
    Skips ahead one or more tracks.
    """

    vc = client.voice_client_in(message.server)
    if not vc:
        await client.send_message(message.channel, ":x: Not currently connected on this server.")
        return

    channels = [vc.channel, find_voice_channel(message.server), message.author.voice_channel]

    if not author_is_valid(message.author, channels):
        await client.send_message(message.channel, ":x: You must be in voice and not deafened to control me.")
        return

    try:
        aaa = message.content.split(" ")
        if aaa[1] == "all":
            to_skip = 9999999
        else:
            to_skip = int(aaa[1])

    except IndexError:
        to_skip = 1
    except ValueError:
        to_skip = 1

    # Await cmd_skip
    s = await vc.cmd_skip(to_skip)

    await client.send_message(message.channel, s)


@command("voteskip")
async def voteskip(client: discord.Client, message: discord.Message):
    """
    Starts a vote to skip the currently playing track.
    """
    # Get the client
    voiceclient = client.voice_client_in(message.server)
    if not voiceclient:
        await client.send_message(message.channel, ":x: Not currently connected on this server.")
        return

    # Check if in voice.
    channels = [voiceclient.channel, find_voice_channel(message.server), message.author.voice_channel]
    if not author_is_valid(message.author, channels):
        await client.send_message(message.channel, ":x: You must be in the same channel as the bot and not deafened.")
        return

    await client.send_message(message.channel, voiceclient.cmd_voteskip(message.author.id))


@command("move", argcount=2, argerror=":x: You must provide two numbers: The original position, and the new position.")
async def move(client: discord.Client, message: discord.Message, fr: int, to: int):
    """
    Moves a song in the queue from position <x> to position <y>.
    """
    vc = client.voice_client_in(message.server)
    if not vc:
        await client.send_message(message.channel, ":x: Not currently connected on this server.")

    fr, to = fr - 1, to - 1

    s = await vc.cmd_move(fr, to)

    await client.send_message(message.channel, s)


@command("remove", roles={"Bot Commander", "Voice", "Admin"},
         argcount="?", argerror=":x: You must give an index to remove.")
async def remove_vid(client: discord.Client, message: discord.Message, *args: list):
    """
    Removes a video at a specific index from the queue.
    """
    vc = client.voice_client_in(message.server)
    if not vc:
        await client.send_message(message.channel, ":x: Not currently connected on this server.")
        return

    if len(args) == 2:
        try:
            fr = int(args[0])
            end = int(args[1])
        except ValueError as e:
            await client.send_message(message.channel, ":x: {}".format(e.args[0]))
            return

    else:
        try:
            fr = int(args[0])
            end = None
        except ValueError as e:
            await client.send_message(message.channel, ":x: {}".format(e.args[0]))
            return

    # Call cmd_remove
    s = await vc.cmd_remove(fr, end)

    await client.send_message(message.channel, s)
