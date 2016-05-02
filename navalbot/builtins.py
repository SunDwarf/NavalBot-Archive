"""
Built-in commands.

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
import os

import discord
import re

from navalbot.api.commands import oldcommand, commands
from navalbot.api import decorators, db
from navalbot.api.util import sanitize, get_file


# Factoid matcher compiled
factoid_matcher = re.compile(r'(\S*?) is (.*)')


@oldcommand("help")
@decorators.enforce_args(1, error_msg=":x: You must provide a command for help!")
async def help(client: discord.Client, message: discord.Message, args: list):
    """
    ಠ_ಠ
    """
    # Get the function
    func = commands.get(args[0])
    if not func:
        await client.send_message(message.channel, ":no_entry: That function does not exist!")
        return

    # Format __doc__
    if not func.__doc__:
        await client.send_message(message.channel, ":x: This function doesn't have help.")
        return
    doc = func.__doc__.split("\n")
    doc = [d.lstrip() for d in doc if d.lstrip()]
    doc = '\n'.join(doc)
    await client.send_message(message.channel, doc)

# region factoids
async def default(client: discord.Client, message: discord.Message):
    prefix = await db.get_config(message.server.id, "command_prefix", "?")
    data = message.content[len(prefix):]
    # Check if it matches a factoid creation
    matches = factoid_matcher.match(data)
    if matches:
        # Set the factoid
        name = matches.groups()[0]
        fac = matches.groups()[1]
        if not (len(name) > 0 and len(fac) > 0):
            return
        # Check if it's locked.
        locked = await db.get_config(message.server.id, "fac:{}:locked".format(name), default=None)
        if locked and locked != message.author.id:
            await client.send_message(message.channel, ":x: Cannot edit, factoid is locked to ID `{}`.".format(locked))
            return
        assert isinstance(fac, str)
        if fac.startswith("http") and 'youtube' not in fac:
            # download as a file
            file = sanitize(fac.split('/')[-1])
            client.loop.create_task(get_file((client, message), url=fac, name=file))
            fac = "file:{}".format(file)
        await db.set_config(message.server.id, "fac:{}".format(name), fac)
        await client.send_message(message.channel, ":heavy_check_mark: Factoid `{}` is now `{}`".format(name, fac))
    else:
        # Load content
        content = await db.get_config(message.server.id, "fac:{}".format(data))
        if not content:
            return
        # Check if it's a file
        if content.startswith("file:"):
            fname = content.split("file:")[1]
            if not os.path.exists(os.path.join(os.getcwd(), 'files', fname)):
                await client.send_message(message.channel, ":x: Unknown error: File {} does not exist".format(fname))
                return
            # Load the file
            with open(os.path.join(os.getcwd(), 'files', fname), 'rb') as f:
                await client.send_file(message.channel, f)
            return
        await client.send_message(message.channel, content)