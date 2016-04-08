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
import asyncio

import discord
import youtube_dl
from discord.voice_client import StreamPlayer, VoiceClient

import util

from cmds import command

voice_params = {"playing": False, "player": None, "file": "", "in_server": None}

loop = asyncio.get_event_loop()

# Create a song queue.
queue = asyncio.Queue(maxsize=100)


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


async def play_music_from_queue():
    # Loads music from the queue and plays it.
    while True:
        music_coro = await queue.get()
        # Await the coroutine
        await music_coro


@command("nowplaying")
@command("np")
async def nowplaying(client: discord.Client, message: discord.Message):
    """
    Displays the currently playing audio.
    """
    if not discord.opus.is_loaded():
        await client.send_message(message.channel, content=":x: Cannot load voice module.")
        return

    if not client.is_voice_connected():
        await client.send_message(message.channel, ":x: I am not in voice currently!")
        return
    if not voice_params["playing"]:
        await client.send_message(message.channel, "No song is currently playing.")
        return
    # Get the player parameter
    player = voice_params["player"]
    assert isinstance(player, StreamPlayer)
    if player.is_done():
        await client.send_message(message.channel, "No song is currently playing.")
        return

    # Return the currently playing song.
    await client.send_message(message.channel, "Currently playing: `{}`".format(voice_params["file"]))


@command("playfile")
@util.with_permission("Bot Commander", "Voice")
@util.enforce_args(1, ":x: You must pass a file parameter!")
async def play_file(client: discord.Client, message: discord.Message, args: list):
    """
    Plays a downloaded file from `files/`.
    You must have the Voice or Bot Commander role to use this command.
    """
    if not discord.opus.is_loaded():
        await client.send_message(message.channel, content=":x: Cannot load voice module.")
        return

    if not client.is_voice_connected():
        await client.send_message(message.channel, ":x: I am not in voice currently!")
        return

    assert isinstance(message.server, discord.Server)
    if message.server.id != voice_params["in_server"]:
        await client.send_message(message.channel, content=":x: Cannot cancel playing from different server!")
        return

    # Get the voice client.
    voice_client = client.voice
    assert isinstance(voice_client, VoiceClient)
    # Check if we're playing something
    if voice_params["playing"]:
        # Get the player.
        player = voice_params["player"]
        assert isinstance(player, StreamPlayer)
        # Stop it.
        player.stop()
        voice_params["playing"] = False
    fname = ' '.join(args[0:])
    # Check to see if the file exists.
    if not os.path.exists(os.path.join(os.getcwd(), 'files', fname)):
        await client.send_message(message.channel, ":x: That file does not exist!")
        return
    # Play it via ffmpeg.
    player = voice_client.create_ffmpeg_player(filename=os.path.join(os.getcwd(), 'files', fname))
    player.start()
    voice_params["player"] = player
    voice_params["playing"] = True
    voice_params["file"] = fname
    await client.send_message(message.channel, ":heavy_check_mark: Now playing: `{}`".format(fname))


@command("stop")
@util.with_permission("Bot Commander", "Voice")
async def stop(client: discord.Client, message: discord.Message):
    """
    Stops the currently playing audio.
    You must have the Voice or Bot Commander role to use this command.
    """
    # Stop playing.
    if not discord.opus.is_loaded():
        await client.send_message(message.channel, content=":x: Cannot load voice module.")
        return

    if not client.is_voice_connected():
        await client.send_message(message.channel, ":x: I am not in voice currently!")
        return

    assert isinstance(message.server, discord.Server)
    if message.server.id != voice_params["in_server"]:
        await client.send_message(message.channel, content=":x: Cannot cancel playing from different server!")
        return

    # Get the voice client.
    voice_client = client.voice
    assert isinstance(voice_client, VoiceClient)
    # Check if we're playing something
    if voice_params["playing"]:
        # Get the player.
        player = voice_params["player"]
        assert isinstance(player, StreamPlayer)
        # Stop it.
        player.stop()
        voice_params["playing"] = False

    await client.send_message(message.channel, ":heavy_check_mark: Stopped playing.")


@command("playyt")
@command("playyoutube")
@util.with_permission("Bot Commander", "Voice")
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

    async def _coro_play_youtube():
        # Coroutine to place on the voice queue.
        # Join the channel.
        await client.join_voice_channel(channel=voice_channel)
        # Get the voice client.
        voice_client = client.voice
        try:
            player = await voice_client.create_ytdl_player(url=vidname)
        except (youtube_dl.utils.ExtractorError, youtube_dl.utils.DownloadError):
            await client.send_message(message.channel, ":x: That is not a valid video!")
            return
        player.start()
        voice_params["player"] = player
        voice_params["playing"] = True
        voice_params["file"] = player.title
        voice_params["in_server"] = message.server.id
        await client.send_message(message.channel, ":heavy_check_mark: Now playing: `{}`".format(player.title))
        # Constantly loop every 0.5s to check if the music has finished.
        while True:
            if player.is_done():
                break
            else:
                await asyncio.sleep(0.5)
        # Leave the voice channel, for the next coroutine to use.
        await client.voice.disconnect()

    # Get the number of songs on the queue.
    items = queue.qsize()

    # Put the coroutine on the queue.
    try:
        queue.put_nowait(_coro_play_youtube())
    except asyncio.QueueFull:
        await client.send_message(message.channel, ":no_entry: There are too many songs on the queue. Cannot start "
                                                   "playing.")
        return
    # We're done! Now we can wait for the player coroutine to await our coro.
    # Send a message to the channel telling them what position they are on.
    if items != 0:
        await client.send_message(message.channel,
                                  ":heavy_check_mark: You are number {} in the queue.".format(items + 1))
    else:
        await client.send_message(message.channel, ":heavy_check_mark: You are next in the queue.")
