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
import db
import discord

import util
from .stores import voice_params

async def find_voice_channel(server: discord.Server):
    # Search for a voice channel with the name specified in the config, and then Music/NavalBot as a fallback.
    cfg_chan = await db.get_config(server.id, "voice_channel", default="")
    for channel in server.channels:
        assert isinstance(channel, discord.Channel)
        if not channel.type == discord.ChannelType.voice:
            continue
        # Check the name.
        if channel.name.lower() in [cfg_chan.lower(), 'music', 'navalbot']:
            chan = channel
            break
    else:
        return None
    return chan


def with_opus(func):
    """
    Ensures Opus is loaded before running the function.
    """
    async def __decorator(client: discord.Client, message: discord.Message):
        if not discord.opus.is_loaded():
            await client.send_message(message.channel, content=":x: Cannot load voice module.")
            return
        else:
            await func(client, message)

    __decorator = util.prov_dec_func(func, __decorator)

    return __decorator


def with_existing_server(func):
    """
    Ensures there's a server instance on the function.
    """
    async def __decorator(client: discord.Client, message: discord.Message):
        if message.server.id not in voice_params:
            await client.send_message(message.channel, content=":x: Not currently connected on this server.")
            return
        else:
            await func(client, message)

    __decorator = util.prov_dec_func(func, __decorator)

    return __decorator
