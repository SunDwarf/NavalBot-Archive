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

import re

import aiohttp
# =============== Commands
from navalbot.api.commands import command
from navalbot.api.contexts import CommandContext

VERSION = "6.0.1"
VERSUFF = ""
VERSIONT = tuple(int(i) for i in VERSION.split("."))


@command("version")
async def version(ctx: CommandContext):
    """
    Checks for the latest stable version of NavalBot.
    """

    # Version info is defined above so it can be reloaded as required.
    await ctx.reply("core.version.base", ver=VERSION + VERSUFF)

    # Download the latest version
    async with aiohttp.ClientSession() as sess:
        s = await sess.get("https://raw.githubusercontent.com/NavalBot/NavalBot-core/develop/navalbot/version.py")
        assert isinstance(s, aiohttp.ClientResponse)
        data = await s.read()
        data = data.decode().split('\n')

    version = read_version(data)
    if not version:
        await ctx.reply("core.version.no_dl")
        return
    if tuple(int(i) for i in version.split(".")) > VERSIONT:
        await ctx.reply("core.version.new_ver", ver=version)
    elif tuple(int(i) for i in version.split(".")) < VERSIONT:
        await ctx.reply("core.version.local_newer", ver=version)
    else:
        await ctx.reply("core.version.same")
