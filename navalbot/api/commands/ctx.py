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
import discord

from navalbot.api.locale import LocaleLoader


class CommandContext:
    """
    This class is a simple thin wrapper that stores a few tidbits of data.
    """
    def __init__(self, client: discord.Client, message: discord.Message, locale: LocaleLoader,
                 args: list=None):
        self.client = client
        self.message = message
        self.locale = locale
        self.args = args

    async def reply(self, key: str, fmt: str=""):
        """
        Wrapper around self.locale["key"] and self.client.send_message(self.message.channel, whatever)
        """
        key = self.locale[key]
        key = key.format(fmt)
        await self.client.send_message(self.message.channel, key)
        return key