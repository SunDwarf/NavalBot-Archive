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

# WEEEEEEEB
import aiohttp

import discord

from cmds import message_hook, command
from exceptions import StopProcessing

# Dict of synonyms
a_synonyms = {
    "SunDwarf": "Kyoukai No Kanata",
    # todo: add more
}

API_BASE = "https://hummingbird.me/api/v1"
API_SEARCH = API_BASE + "/search/anime"

async def search_shows(to_search: str):
    """
    Search for a show.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(API_SEARCH, params={"query": to_search}) as req:
            assert isinstance(req, aiohttp.ClientResponse)
            res = await req.json()
            return res


@message_hook
async def on_chinese_cartoon(client: discord.Client, message: discord.Message):
    """
    Runs if the message begins with { and ends with }.
    """
    assert isinstance(message.content, str)
    if not (message.content.startswith("{") and message.content.endswith("}")):
        return

    # Get [1:-1] to strip the leading brackets.
    show = message.content[1:-1]
    # check synonym
    if show in a_synonyms:
        show = a_synonyms[show]

    show_searched = await search_shows(show)
    result = show_searched[0]

    formatted = "**{title}** Status: `{status}`\n\n{synopsis}\n{url}".format(**result)

    await client.send_message(message.channel, formatted)

    raise StopProcessing