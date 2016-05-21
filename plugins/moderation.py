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
import asyncio
import json
import os
import re

import discord

from navalbot.api import db
from navalbot.api.commands import command
from navalbot.api.commands.cmdclass import NavalRole
from navalbot.exceptions import CommandError

VERSION = "1.0.1"


@command("mute", roles={NavalRole.ADMIN, NavalRole.BOT_COMMANDER})
async def mute(client: discord.Client, message: discord.Message):
    """
    Mutes a user. This user must be @mentioned.
    You must a have `Muted` role installed on the server.
    """
    muterole = discord.utils.get(message.server.roles, name='Muted')

    if not muterole:
        raise CommandError('No Muted role created')

    if len(message.mentions) > 0:
        try:
            await client.add_roles(message.mentions[0], muterole)
            await client.server_voice_state(message.mentions[0], mute=True)
            await client.send_message(message.channel,
                                      'User {} got muted by {}'.format(message.mentions[0], message.author))
        except discord.Forbidden:
            await client.send_message('Not enough permissions to mute user {}'.format(message.mentions[0].name))
            raise CommandError('Not enough permissions to mute user : {}'.format(message.mentions[0].name))
    else:
        prefix = await db.get_config(message.server.id, "command_prefix", "?")
        await client.send_message(message.channel, "Usage: {}mute @UserName".format(prefix))


@command("unmute", roles={NavalRole.ADMIN, NavalRole.BOT_COMMANDER})
async def unmute(client: discord.Client, message: discord.Message):
    """
    Unmutes a user. This user must be @mentioned.
    You must a have `Muted` role installed on the server.
    """
    muterole = discord.utils.get(message.server.roles, name='Muted')

    if not muterole:
        raise CommandError('No Muted role created')
    if len(message.mentions) > 0:
        try:
            await client.remove_roles(message.mentions[0], muterole)
            await client.server_voice_state(message.mentions[0], mute=False)
            await client.send_message(message.channel,
                                      'User {} got unmuted by {}'.format(message.mentions[0], message.author))
        except discord.Forbidden:
            await client.send_message('Not enough permissions to unmute user {}'.format(message.mentions[0].name))
            raise CommandError('Not enough permissions to unmute user : {}'.format(message.mentions[0].name))
    else:
        prefix = await db.get_config(message.server.id, "command_prefix", "?")
        await client.send_message(message.channel, "Usage: {}unmute @UserName".format(prefix))


@command("ban", roles={NavalRole.ADMIN})
async def ban(client: discord.Client, message: discord.Message):
    """
    Bans a user from the server.
    """
    try:
        await client.ban(member=message.mentions[0]) \
            if len(message.mentions) > 0 \
            else client.send_message(message.channel, content=":question: You must provide a user to ban.")
        await client.send_message(message.channel,
                                  '{} got banned by {}!'.format(message.mentions[0], message.author.name))
    except (discord.Forbidden, IndexError) as banerror:
        print('[ERROR]:', banerror)


@command("kick", roles={NavalRole.ADMIN})
async def kick(client: discord.Client, message: discord.Message):
    """
    Kicks a user from the server.
    """
    try:
        await client.kick(member=message.mentions[0])
        await client.send_message(message.channel,
                                  '{} got kicked by {}!'.format(message.mentions[0], message.author.name))
    except (discord.Forbidden, IndexError) as kickerror:
        print('[Error]', kickerror)


@command("delete", roles={NavalRole.ADMIN})
async def delete(client: discord.Client, message: discord.Message):
    """
    Prunes a certain number of messages from the server.
    """
    try:
        count = int(' '.join(message.content.split(" ")[1:]))
    except ValueError:
        await client.send_message(message.channel, "This is not a number")
        return

    if count is None:
        return
    async for msg in client.logs_from(message.channel, count + 1):
        await asyncio.sleep(0.25)
        await client.delete_message(msg)
    if count == 1:
        await client.send_message(message.channel, ':wastebasket: **{} message deleted by {}**'
                                  .format(count, message.author))
    else:
        await client.send_message(message.channel, ':wastebasket: **{} messages deleted by {}**'
                                  .format(count, message.author))


@command("invite")
async def invite(client: discord.Client, message: discord.Message):
    """
    Accepts an invite to another server.
    """

    if client.user.bot:
        await client.send_message(":X: Cannot accept invite as a bot account.")
        return
    try:
        invite = message.content.split(" ")[1]
    except IndexError:
        prefix = await db.get_config(message.server.id, "command_prefix", "?")
        await client.send_message(message.channel, "Usage: {}invite [link]".format(prefix))
        return

    await client.accept_invite(invite)
    await client.send_message(message.channel, "Joined server specified.")


@command("banned", owner=True)
async def banned(client: discord.Client, message: discord.Message):
    """
    Get a list of all currently banned users on a server.
    """
    users = await client.get_bans(server=message.server)
    await client.send_message(message.channel, "Banned users: {}".format(', '.join(user.name for user in users)))


@command("blacklist", roles={NavalRole.ADMIN}, argcount="?", argerror=":x: You must select at least one user to blacklist!")
async def blacklist(client: discord.Client, message: discord.Message, *_: list):
    """
    Blocks a user from communicating with the bot.
    """
    if os.path.exists("blacklist.json"):
        with open("blacklist.json") as f:
            black_list = json.load(f)
    else:
        black_list = {}
    for user in message.mentions:
        if message.server.id not in black_list:
            black_list[message.server.id] = []
        if user not in black_list[message.server.id]:
            black_list[message.server.id].append(user.id)
    await client.send_message(message.channel, ":heavy_check_mark: User(s) `{}` added to the blacklist."
                              .format(' '.join(u.name for u in message.mentions)))
    with open("blacklist.json", 'w') as f:
        json.dump(black_list, f)


@command("unblacklist", roles={NavalRole.ADMIN}, args=1)
async def unblacklist(client: discord.Client, message: discord.Message, *_: list):
    """
    Unblocks a user from communicating with the bot.
    """
    if os.path.exists("blacklist.json"):
        with open("blacklist.json") as f:
            black_list = json.load(f)
    else:
        black_list = {}
    for user in message.mentions:
        if message.server.id in black_list:
            if user.id in black_list[message.server.id]:
                black_list[message.server.id].remove(user.id)
    await client.send_message(message.channel, ":heavy_check_mark: User(s) `{}` removed from the blacklist."
                              .format(' '.join(u.name for u in message.mentions)))
    with open("blacklist.json", 'w') as f:
        json.dump(black_list, f)


@command("broadcast", owner=True)
async def broadcast(client: discord.Client, message: discord.Message):
    """
    Sends a message to all servers the bot is connected to.
    """
    text = message.content.split(" ")[1]
    for servers in client.servers:
        await client.send_message(servers, "*Broadcast message:* {}".format(text))


@command("changecolor", roles={NavalRole.BOT_COMMANDER}, argcount=1, argerror="You must provide a hex color")
async def colour(client: discord.Client, message: discord.Message, hexa: str):
    """
    Changes the color of a user. The color needs to be supplied in a hexadecimal format without the `#`!
    """

    def find_role():
        for i, val in enumerate(message.author.roles):
            if re.search('_colour', str(val)):
                return str(val)

    try:
        color = discord.Colour(int(hexa, 16))
        role = discord.utils.get(message.server.roles, name=str(find_role()))
        await client.edit_role(message.server, role, colour=color)
        await client.send_message(message.channel, "Color got changed!")
    except discord.Forbidden:
        await client.send_message('Not enough permissions to change color')
    except ValueError:
        await client.send_message(message.channel, "Please provide a valid hexadecimal number without the `#`!")
