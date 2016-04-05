import os

import discord
from discord.voice_client import StreamPlayer, VoiceClient

import util

from cmds import command

voice_channel = []
voice_params = {"playing": False, "player": None, "file": ""}


@command("joinvoice")
@util.with_permission("Bot Commander")
async def join_voice_channel(client: discord.Client, message: discord.Message):
    if client.is_voice_connected():
        await voice_channel.pop().disconnect()
    # Get the server.
    server = message.server
    # Get the voice channel.
    split = message.content.split(" ")
    if len(split) < 2:
        await client.send_message(message.channel, ":x: You must provide a channel!")
        return
    else:
        to_join = split[1]
    # Try and find the voice channel.
    channel = discord.utils.get(server.channels, name=to_join, type=discord.ChannelType.voice)
    if not channel:
        await client.send_message(
            message.channel,
            ":x: The channel `{}` does not exist on this server!".format(to_join))
        return
    # Join the channel.
    voice = await client.join_voice_channel(channel)
    voice_channel.append(voice)
    await client.send_message(message.channel, ":heavy_check_mark: Joined voice channel!")


@command("leavevoice")
@util.with_permission("Bot Commander")
async def leave_voice_channels(client: discord.Client, message: discord.Message):
    if not client.is_voice_connected():
        await client.send_message(message.channel, ":x: I am not in voice currently!")
    else:
        await voice_channel.pop().disconnect()
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
@util.with_permission("Bot Commander")
async def play_file(client: discord.Client, message: discord.Message):
    if not client.is_voice_connected():
        await client.send_message(message.channel, ":x: I am not in voice currently!")
        return
    # Get the voice client.
    voice_client = voice_channel[0]
    assert isinstance(voice_client, VoiceClient)
    # Check if we're playing something
    if voice_params["playing"]:
        # Get the player.
        player = voice_params["player"]
        assert isinstance(player, StreamPlayer)
        # Stop it.
        player.stop()
        voice_params["playing"] = False
    # Get the filename.
    split = message.content.split(" ")
    if len(split) < 2:
        await client.send_message(message.channel, ":x: You must pass a file parameter!")
        return
    fname = ' '.join(split[1:])
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
