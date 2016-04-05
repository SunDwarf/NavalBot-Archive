import discord

import util
from cmds import command

voice_channel = []


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
        await client.send_message(message.channel, ":no_entry: You must provide a channel!")
        return
    else:
        to_join = split[1]
    # Try and find the voice channel.
    channel = discord.utils.get(server.channels, name=to_join, type=discord.ChannelType.voice)
    if not channel:
        await client.send_message(
            message.channel,
            ":no_entry: The channel `{}` does not exist on this server!".format())
        return
    # Join the channel.
    voice = await client.join_voice_channel(channel)
    voice_channel.append(voice)
    await client.send_message(message.channel, ":heavy_check_mark: Joined voice channel!")


@command("leavevoice")
@util.with_permission("Bot Commander")
async def leave_voice_channels(client: discord.Client, message: discord.Message):
    if not client.is_voice_connected():
        await client.send_message(message.channel, ":no_entry: I am not in voice currently!")
    else:
        await voice_channel.pop().disconnect()
