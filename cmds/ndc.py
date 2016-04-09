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

# RCE ids
import cmds
import util

loop = asyncio.get_event_loop()


#@cmds.command("sql")
async def sql(client: discord.Client, message: discord.Message):
    if not int(message.author.id) in cmds.RCE_IDS:
        await client.send_message(message.channel, "You're not Sun")
        return
    else:
        sql_cmd = ' '.join(message.content.split(' ')[1:])
        util.cursor.execute(sql_cmd)


#@cmds.command("py")
async def py(client: discord.Client, message: discord.Message):
    if not int(message.author.id) in cmds.RCE_IDS:
        await client.send_message(message.channel, "You're not Sun")
        return
    else:
        cmd = ' '.join(message.content.split(' ')[1:])

        def smsg(content):
            loop.create_task(client.send_message(message.channel, '`' + content + '`'))

        def ec(cmd):
            data = subprocess.check_output(cmd, shell=True)
            data = data.decode().replace('\n', '')
            smsg(data)

        exec(cmd)
