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

# Commands designed for Naval.TF's discord.

import discord
import subprocess
import asyncio
import re

# RCE ids
import cmds
import util

getter = re.compile(r'`{1,3}(.*?)`{1,3}')

loop = asyncio.get_event_loop()


@cmds.command("sql")
async def sql(client: discord.Client, message: discord.Message):
    if not int(message.author.id) in cmds.RCE_IDS:
        await client.send_message(message.channel, "You're not Sun")
        return
    else:
        sql_cmd = ' '.join(message.content.split(' ')[1:])
        util.cursor.execute(sql_cmd)


@cmds.command("py")
@util.only(util.get_config(None, "RCE_ID", default=0, type_=int))
async def py(client: discord.Client, message: discord.Message):
    match = getter.findall(message.content)
    if not match:
        return
    else:
        result = exec(match[0])
        await client.send_message(message.channel, "```{}```".format(result))