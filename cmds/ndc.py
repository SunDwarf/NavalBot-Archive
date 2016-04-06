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

from valve.source import a2s

import bot

# RCE ids
import cmds
import util

# Servers for fetching
SERVERS = [
    ("yamato.tf.naval.tf", 27015),
    ("musashi.tf.naval.tf", 27015),
    ("gorch.tf.naval.tf", 27015),
    ("gorch.tf.naval.tf", 27016),
    ("gorch.tf.naval.tf", 27017),
    ("prinzeugen.tf.naval.tf", 27015),
    ("prinzeugen.tf.naval.tf", 27016),
    ("prinzeugen.tf.naval.tf", 27017)
]


@cmds.command("sql")
async def sql(client: discord.Client, message: discord.Message):
    if not int(message.author.id) in bot.RCE_IDS:
        await client.send_message(message.channel, "You're not Sun")
        return
    else:
        sql_cmd = ' '.join(message.content.split(' ')[1:])
        util.cursor.execute(sql_cmd)


@cmds.command("py")
async def py(client: discord.Client, message: discord.Message):
    if not int(message.author.id) in bot.RCE_IDS:
        await client.send_message(message.channel, "You're not Sun")
        return
    else:
        cmd = ' '.join(message.content.split(' ')[1:])

        def smsg(content):
            bot.loop.create_task(client.send_message(message.channel, '`' + content + '`'))

        def ec(cmd):
            data = subprocess.check_output(cmd, shell=True)
            data = data.decode().replace('\n', '')
            smsg(data)

        exec(cmd)


@cmds.command("servers")
async def servers(client: discord.Client, message: discord.Message):
    await client.send_message(message.channel, "**Servers:**")
    for num, serv in enumerate(SERVERS):
        querier = a2s.ServerQuerier(serv, timeout=0.5)
        try:
            info = bot.attrdict(querier.info())
        except a2s.NoResponseError:
            await client.send_message(
                message.channel,
                content="**Server {num}:** `({t[0]}:{t[1]})` - not responding\n".format(t=serv, num=num + 1)
            )
        else:
            await client.send_message(
                message.channel,
                content="**Server {num}:** {q.server_name} - `{q.map}` - `{q.player_count}/{q.max_players}`"
                            .format(q=info, num=num + 1) + " - steam://connect/{t[0]}:{t[1]}".format(t=serv))
