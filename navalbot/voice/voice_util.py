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
import discord

from navalbot.api import db, util
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


def author_is_valid(author: discord.Member, valid_channels: list):
    """
    Check if an author is valid for skipping.
    """
    in_voice = author.voice_channel is not None
    in_one_of = author.voice_channel in valid_channels
    deafened = (author.deaf or author.self_deaf)
    return in_voice and in_one_of and not deafened