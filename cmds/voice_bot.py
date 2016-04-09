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
import logging
import asyncio

import discord
import functools
import youtube_dl
from discord.voice_client import StreamPlayer, VoiceClient

import cmds
import util

from cmds import command

loop = asyncio.get_event_loop()

voice_params = {}


async def find_voice_channel(server: discord.Server):
    # Search for a voice channel called 'Music' or 'NavalBot'.
    for channel in server.channels:
        assert isinstance(channel, discord.Channel)
        if not channel.type == discord.ChannelType.voice:
            continue
        # Check the name.
        if channel.name.lower() in ['music', 'navalbot']:
            chan = channel
            break
    else:
        return None
    return chan


async def _await_queue(server_id: str):
    # Awaits new songs on the queue.
    queue = voice_params[server_id]["queue"]
    while True:
        try:
            items = await queue.get()
        except RuntimeError:
            return
        # Await the playing coroutine.
        await items[0]


@command("np")
@command("nowplaying")
async def np(client: discord.Client, message: discord.Message):
    # Get the current player instance.
    if not discord.opus.is_loaded():
        await client.send_message(message.channel, content=":x: Cannot load voice module.")
        return

    if message.server.id not in voice_params:
        await client.send_message(message.channel, content=":x: Not currently connected on this server.")
        return

    playing = voice_params[message.server.id].get("playing")
    if not playing:
        await client.send_message(message.channel, content=":x: No song is currently playing on this server.")
        return

    player = voice_params[message.server.id].get("player")
    if not player:
        # ???
        await client.send_message(message.channel, content=":x: No song is currently playing on this server.")
        return

    title = voice_params[message.server.id].get("title", "??? Internal error")
    await client.send_message(message.channel, content="Currently playing: `{}`".format(title))


@command("queued")
@command("queue")
async def get_queued_vids(client: discord.Client, message: discord.Message):
    # STILL HORRIBLE

    # Get the current player instance.
    if not discord.opus.is_loaded():
        await client.send_message(message.channel, content=":x: Cannot load voice module.")
        return

    if message.server.id not in voice_params:
        await client.send_message(message.channel, content=":x: Not currently connected on this server.")
        return

    queue = voice_params[message.server.id].get('queue', [])
    if queue:
        queue = queue._queue

    s = "**Currently queued:**"
    if len(queue) == 0:
        s += "\n`Nothing is queued.`"
        await client.send_message(message.channel, s)
        return

    for item in range(0, len(queue)):
        i = queue[item]
        title = i[1].get('title')
        s += "\n{}. `{}`".format(item + 1, title)
    await client.send_message(message.channel, s)


@command("stop")
@util.with_permission("Bot Commander", "Voice", "Admin")
async def stop_vid(client: discord.Client, message: discord.Message):
    """
    Stops the current track being played on the server.
    You must have the Voice or Bot Commander role to use this command.
    """
    # Get the current player instance.
    if not discord.opus.is_loaded():
        await client.send_message(message.channel, content=":x: Cannot load voice module.")
        return

    if message.server.id not in voice_params:
        await client.send_message(message.channel, content=":x: Not currently connected on this server.")
        return

    playing = voice_params[message.server.id].get("playing")
    if not playing:
        await client.send_message(message.channel, content=":x: No song is currently playing on this server.")
        return

    player = voice_params[message.server.id].get("player")
    if not player:
        # ???
        await client.send_message(message.channel, content=":x: No song is currently playing on this server.")
        return

    # Finally, stop the player.
    player.stop()
    await client.send_message(message.channel, content=":heavy_check_mark: Stopped current song.")


@command("play")
@command("playyt")
@command("playyoutube")
@util.enforce_args(1, ":x: You must pass a video!")
async def play_youtube(client: discord.Client, message: discord.Message, args: list):
    """
    Plays a video from any valid streaming source that `youtube-dl` can download from.
    This included things such as YouTube (obviously) and SoundCloud.
    You must have the Voice or Bot Commander role to use this command.
    """
    if not discord.opus.is_loaded():
        await client.send_message(message.channel, content=":x: Cannot load voice module.")
        return

    voice_channel = await find_voice_channel(message.server)
    if not voice_channel:
        await client.send_message(message.channel, content=":x: Cannot find voice channel for playing music! (channel "
                                                           "must be named `Music` or `NavalBot`.)")
        return

    vidname = args[0]

    # Do the same as play_file, but with a youtube streamer.
    # Play it via ffmpeg.

    ydl = youtube_dl.YoutubeDL({"format": 'webm[abr>0]/bestaudio/best'})
    func = functools.partial(ydl.extract_info, vidname, download=False)
    info = await loop.run_in_executor(None, func)
    if "entries" in info:
        info = info['entries'][0]

    title = info.get('title')
    download_url = info['url']

    duration = info.get('duration')
    if (duration and int(duration) > (60 * 10)) and int(message.author.id) not in cmds.RCE_IDS:
        await client.send_message(message.channel, ":x: Videos are limited to a maximum of 10 minutes.")
        return

    # Contrary to the name, this file DOES use queues.
    # However, unlike voice_queue, OAuth2 bots can run on multiple voice servers at once.
    # This means multiple queues can be used per bot.

    # What this coroutine does:
    # 1. Checks for the queue of a specific server.
    #    If it doesn't find one, it creates a new one. It then opens a new voice connection to the server.
    # 2. Places the coroutine on the server-specific queue.
    # 3. Checks to see if there is a looping task running for fetching new songs off of the queue for that server.
    #    If there isn't, it will create a new one, store it, and so on.

    # Check for the queue.
    if message.server.id not in voice_params:
        # Nope!
        voice_params[message.server.id] = {}
    if 'queue' not in voice_params[message.server.id]:
        voice_params[message.server.id]["queue"] = asyncio.Queue(maxsize=99)

    queue = voice_params[message.server.id]["queue"]

    # Get the voice client.
    if message.server.id not in client.voice:
        voice_client = await client.join_voice_channel(channel=voice_channel)
    else:
        voice_client = client.voice[message.server.id]

    async def _oauth2_play_youtube():
        # Much smaller than voice_queue, as we don't have to do fucky logic.
        player = voice_client.create_ffmpeg_player(download_url)
        voice_params[message.server.id]["playing"] = True
        voice_params[message.server.id]["title"] = title
        voice_params[message.server.id]["player"] = player
        await client.send_message(message.channel, ":heavy_check_mark: Now playing: `{}`".format(title))
        # Start playing
        player.start()
        # Check ever 0.5 seconds if we're done or not.
        # 0.5 is non-noticable delay, but doesn't kill the CPU.
        while True:
            if player.is_done():
                break
            else:
                await asyncio.sleep(0.5)
        # Reset everything after it's done.
        voice_params[message.server.id]["playing"] = False
        voice_params[message.server.id]["title"] = ""
        voice_params[message.server.id]["player"] = None

    # Get the number of songs on the queue.
    items = queue.qsize()

    try:
        queue.put_nowait((_oauth2_play_youtube(), info))
    except asyncio.QueueFull:
        await client.send_message(message.channel, ":no_entry: There are too many songs on the queue. Cannot start "
                                                   "playing.")
    # Send a helpful error message.
    if items != 0:
        await client.send_message(message.channel,
                                  ":heavy_check_mark: You are number {} in the queue.".format(items + 1))
    else:
        await client.send_message(message.channel, ":heavy_check_mark: You are next in the queue.")

    # Create a new task, if applicable.
    if 'task' not in voice_params[message.server.id]:
        # Create the new task.
        task = loop.create_task(_await_queue(message.server.id))
        voice_params[message.server.id]["task"] = task
