# Commands designed for Naval.TF's discord.

import discord
import subprocess

from valve.source import a2s

import bot

# RCE ids
import cmds

RCE_IDS = [
    141545699442425856
]

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
    if not int(message.author.id) in RCE_IDS:
        await client.send_message(message.channel, "You're not Sun")
        return
    else:
        sql_cmd = ' '.join(message.content.split(' ')[1:])
        bot.cursor.execute(sql_cmd)


@cmds.command("py")
async def py(client: discord.Client, message: discord.Message):
    if not int(message.author.id) in RCE_IDS:
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
