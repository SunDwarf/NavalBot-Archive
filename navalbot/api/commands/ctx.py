"""
Context class.

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
import typing

import aioredis
import discord

from navalbot.api import db
from navalbot.api.locale import LocaleLoader
from navalbot.api.util import get_pool


class CommandContext:
    """
    This class is a simple thin wrapper that stores a few tidbits of data.
    """

    def __init__(self, client: discord.Client, message: discord.Message, locale: LocaleLoader,
                 args: list = None):
        self.client = client
        self.message = message
        self.locale = locale
        self.args = args

        # Other useful properties.
        self.server = self.message.server
        assert isinstance(self.server, discord.Server)

        self.author = self.message.author

        self.channel = self.message.channel
        self.me = self.server.me
        if self.me is not None:
            assert isinstance(self.me, discord.Member)

        self.db = db

    async def get_config(self, name, default=None, type_: type = str):
        """
        Gets a config value from the database for a server-specific var.
        """
        return await db.get_config(self.server.id, name, default=default, type_=type_)

    async def set_config(self, name, value):
        """
        Sets a config value from the database for a server-specific var.
        """
        await db.set_config(self.server.id, name, value)

    async def get_conn(self) -> aioredis.RedisConnection:
        pool = await get_pool()
        return pool.get()

    async def delete_config(self, name):
        """
        Deletes a config value from the DB.
        """
        await db.delete_config(self.server.id, name)

    async def reply(self, key: str, **fmt):
        """
        Wrapper around self.locale["key"] and self.client.send_message(self.message.channel, whatever)
        """
        key = self.locale[key]
        key = key.format(**fmt)
        await self.client.send_message(self.message.channel, key)
        return key

    async def send(self, message: str):
        """
        Send a message to the channel.
        """
        await self.client.send_message(self.channel, message)

    def get_user(self) -> typing.Union[discord.Member, None]:
        """
        Attempts to get a user from the message.
        """
        if len(self.message.mentions) >= 1:
            return self.message.mentions[0]
        if len(self.args) >= 1:
            u = self.message.server.get_member_named(' '.join(self.args))
            return u
