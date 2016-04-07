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


@command("joinvoice")
@util.with_permission("Bot Commander", "Voice")
@util.enforce_args(1, ":x: You must provide a channel!")
async def join_voice_channel(client: discord.Client, message: discord.Message, args: list):
    if not discord.opus.is_loaded():
        await client.send_message(message.channel, content=":x: Cannot load voice module.")
        return

    if client.is_voice_connected():
        assert isinstance(message.server, discord.Server)
        if message.server.id == voice_params["in_server"]:
            await client.voice.disconnect()
            if voice_params["playing"]:
                # Get the player.
                player = voice_params["player"]
                assert isinstance(player, StreamPlayer)
                # Stop it.
                player.stop()
                voice_params["playing"] = False
        else:
            await client.send_message(message.channel, content=":x: Cannot cancel playing from different server!")
            return
    # Get the server.
    server = message.server
    # Get the voice channel.
    to_join = ' '.join(args[0:])
    # Try and find the voice channel.
    channel = discord.utils.get(server.channels, name=to_join, type=discord.ChannelType.voice)
    if not channel:
        await client.send_message(
            message.channel,
            ":x: The channel `{}` does not exist on this server!".format(to_join))
        return
    # Join the channel.
    await client.join_voice_channel(channel)
    # Set the server ID.
    voice_params["in_server"] = message.server.id
    await client.send_message(message.channel, ":heavy_check_mark: Joined voice channel!")


@command("leavevoice")
@util.with_permission("Bot Commander", "Voice")
async def leave_voice_channels(client: discord.Client, message: discord.Message):
    if not discord.opus.is_loaded():
        await client.send_message(message.channel, content=":x: Cannot load voice module.")
        return

    if not client.is_voice_connected():
        await client.send_message(message.channel, ":x: I am not in voice currently!")
    else:
        assert isinstance(message.server, discord.Server)
        if message.server.id == voice_params["in_server"]:
            await client.voice.disconnect()
            voice_params["in_server"] = None
        else:
            await client.send_message(message.channel, content=":x: Cannot cancel playing from different server!")
            return
        if voice_params["playing"]:
            # Get the player.
            player = voice_params["player"]
            assert isinstance(player, StreamPlayer)
            # Stop it.
            player.stop()
            voice_params["playing"] = False


@command("nowplaying")
@command("np")
async def nowplaying(client: discord.Client, message: discord.Message):
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
@util.with_permission("Bot Commander")
async def stop(client: discord.Client, message: discord.Message):
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
@util.with_permission("Bot Commander")
@util.enforce_args(1, ":x: You must pass a video!")
async def play_youtube(client: discord.Client, message: discord.Message, args: list):
    if not discord.opus.is_loaded():
        await client.send_message(message.channel, content=":x: Cannot load voice module.")
        return

    # Standard checks.
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

    vidname = args[0]
    # Do the same as play_file, but with a youtube streamer.
    # Play it via ffmpeg.
    try:
        player = await voice_client.create_ytdl_player(url=vidname)
    except (youtube_dl.utils.ExtractorError, youtube_dl.utils.DownloadError):
        await client.send_message(message.channel, ":x: That is not a valid video!")
        return
    player.start()
    voice_params["player"] = player
    voice_params["playing"] = True
    voice_params["file"] = player.title
    await client.send_message(message.channel, ":heavy_check_mark: Now playing: `{}`".format(player.title))
