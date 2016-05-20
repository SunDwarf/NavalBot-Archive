"""
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

import inspect
import shlex

import discord

from navalbot import exceptions
from navalbot.api import util, db
from navalbot.api.util import has_permissions_with_override


class NavalRole:
    ADMIN = 1
    BOT_COMMANDER = 2
    VOICE = 4


class Command(object):
    """
    This represents a command, used by the bot.

    These classes should never be created directly, only via the @command decorator, which provides it with the
    correct arguments.

    Commands are invoked with .invoke(), but this is only used in on_message.
    """

    def __init__(self, to_wrap, *names, **kwargs):
        # Declare everything
        self.names = names
        self._wrapped_coro = to_wrap

        self._parse_kwargs(**kwargs)

    def _parse_kwargs(self, **kwargs):
        """
        Parse kwargs.
        """

        if kwargs.get("argcount"):
            # If it's ?, supply it as a list.
            if kwargs["argcount"] == "?":
                # 0 -> List of args, used for multiple.
                self._args_type = 0
                self._args_count = None
            else:
                self._args_type = 1
                self._args_count = int(kwargs["argcount"])

        # Role restrictions.
        if kwargs.get("roles"):
            roles = kwargs.get("roles")
            if isinstance(roles, str):
                self._roles = {roles}
            else:
                self._roles = set(roles)

        # ID restriction
        if kwargs.get("owner"):
            self._only_owner = kwargs["owner"]
        else:
            self._only_owner = False

    def help(self):
        """
        Get the help for a specific function.
        """
        doc = self._wrapped_coro.__doc__.split("\n")
        doc = [d.lstrip() for d in doc if d.lstrip()]
        doc = '\n'.join(doc)

        return doc

    async def _construct_arg_error_msg(self, server: discord.Server):
        prefix = await db.get_config(server.id, "command_prefix", default="?")
        base = """```{}({})""".format(prefix, '|'.join(self.names))

        if self._args_type == 0:
            base += " <1 or more arguments>\n\n"
        elif self._args_type == 1:
            base += " <{} arguments>\n\n".format(self._args_count)

        base += self.help() + "\n```"

        return base

    async def invoke(self, client: discord.Client, message: discord.Message):
        """
        Invoke the function.
        """
        # Do the checks before running the coroutine.
        # Owner check.

        if self._only_owner:
            owner = util.get_global_config("RCE_ID", default=0, type_=int)
            u_id = int(message.author.id)
            # Check if it is in the ids specified.
            if not u_id == owner:
                await client.send_message(message.channel, ":no_entry: This command is restricted to bot owners.")
                return
        # Role check.

        # Get the user's roles.
        if hasattr(self, "_roles"):
            allowed_roles = self._roles
            try:
                assert isinstance(message.author, discord.Member)
            except AssertionError:
                await client.send_message(message.channel, ":no_entry: Cannot determine your role!")
                return
            if not await has_permissions_with_override(message.author, allowed_roles, message.server.id,
                                                       self._wrapped_coro.__name__):
                await client.send_message(
                    message.channel,
                    ":no_entry: You do not have any of the required roles: `{}`!".format(allowed_roles)

                )
                return

        # Arguments check.
        if hasattr(self, "_args_type"):
            if self._args_type == 0:
                # Split out the args into a list.
                try:
                    args = shlex.split(message.content)[1:]
                except ValueError:
                    args = message.content.split(" ")[1:]
                if len(args) < 1:
                    await client.send_message(message.channel, await self._construct_arg_error_msg(message.server))
                    return
            elif self._args_type == 1:
                # Check the function for annotations.
                func_sig = inspect.signature(self._wrapped_coro)
                if len(func_sig.parameters) != (2 + self._args_count):
                    raise exceptions.BadCommandException("Arg count of {} differs from number of requested args ({})"
                                                         .format(len(func_sig.parameters), 2 + self._args_count))
                # Get the annotations, if applicable.
                params = list(func_sig.parameters.values())
                annotations = [f.annotation for f in params[2:]]
                temp_args = shlex.split(message.content)[1:]
                if len(temp_args) != self._args_count:
                    await client.send_message(message.channel, self._arg_error_msg)
                    return
                args = []
                # match the annotations
                for arg, ann in zip(temp_args, annotations):
                    if ann == inspect.Parameter.empty:
                        args.append(arg)
                    else:
                        # Nested doom
                        if isinstance(ann, type):
                            if ann.__name__ == "bool":
                                args.append(False if arg == "False" else True)
                            else:
                                try:
                                    args.append(ann(arg))
                                except ValueError:
                                    await client.send_message(message.channel, ":x: One of your arguments was the "
                                                                               "wrong type.")
                                    return

        # Now that we've gotten all of the returns out of the way, invoke the coroutine.
        if hasattr(self, "_args_type"):
            result = await self._wrapped_coro(client, message, *args)
        else:
            result = await self._wrapped_coro(client, message)

        if result:
            await client.send_message(message.channel, result)
