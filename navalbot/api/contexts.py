"""
Contexts - contains files for contexts, such as CommandContext or EventContext.
"""
import typing

import aioredis

import discord
from navalbot.api import db
from navalbot.api import botcls
from navalbot.api.locale import LocaleLoader
from navalbot.api.util import get_pool


class Context:
    """
    A context is a simple way of storing attributes about an event or command.
    """

    def __init__(self, client: 'botcls.NavalClient'):
        """
        Simple stub for the context class.
        """
        self.client = client


class EventContext(Context):
    """
    An event context is passed to `on_` events.

    It contains certain fields to be used, depending on the event.

    This is normally subclassed. The event will automatically load the correct fields to be consistent
    depending on the event.

    This event will throw errors if you attempt to access a property that doesn't exist in a specific event.
    """

    @property
    def server(self) -> discord.Server:
        raise NotImplementedError

    @property
    def member(self) -> discord.Member:
        raise NotImplementedError

    @property
    def channel(self) -> discord.Channel:
        raise NotImplementedError

    @property
    def message(self) -> discord.Message:
        raise NotImplementedError

    def get_named_user(self, name: str) -> typing.Union[discord.Member, None]:
        """
        Gets a user by name from the server.
        """
        return self.server.get_member_named(name)

    def get_member_by_name_or_id(self, search: str) -> typing.Union[discord.Member, None]:
        """
        Attempts to get a user by ID or name.
        """
        u = self.server.get_member(search)
        if not u:
            u = self.get_named_user(search)
        return u

    def get_channel(self, name_or_id) -> discord.Channel:
        """
        Gets a channel by name or ID from the server.
        """
        chan = self.server.get_channel(name_or_id)
        if not chan:
            chan = discord.utils.get(self.server.channels, name=name_or_id)
        return chan


class OnMessageEventContext(EventContext):
    """
    Context for on_message events.
    """

    def __init__(self, client: 'botcls.NavalClient', message: discord.Message, locale: LocaleLoader):
        super().__init__(client)

        self._message = message
        self._locale = locale

    @property
    def server(self):
        return self._message.server

    @property
    def member(self):
        return self._message.author

    @property
    def channel(self):
        return self._message.channel

    @property
    def message(self):
        return self._message

    @property
    def loc(self):
        return self._locale

    async def reply(self, key: str, **fmt):
        """
        Wrapper around self.locale["key"] and self.client.send_message(self.message.channel, whatever)
        """
        key = self._locale[key]
        key = key.format(**fmt)
        await self.client.send_message(self.message.channel, key)
        return key


class CommandContext(OnMessageEventContext):
    """
    This class is a simple thin wrapper that stores a few tidbits of data.
    """

    def __init__(self, client: 'botcls.NavalClient', message: discord.Message, locale: LocaleLoader,
                 args: list = None):
        super().__init__(client, message, locale)
        self.locale = locale
        self.args = args

        self.db = db

    @property
    def server(self) -> discord.Server:
        return self.message.server

    @property
    def channel(self) -> discord.Channel:
        return self.message.channel

    @property
    def me(self) -> discord.Member:
        return self.server.me

    @property
    def author(self) -> discord.Member:
        return self.message.author

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

