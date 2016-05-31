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
from navalbot.api.commands.ctx import CommandContext
from navalbot.api.util import has_permissions_with_override
from navalbot.api.locale import get_locale


class _RoleProxy:
    def __init__(self, order, name, val):
        self.name = name
        self.val = val

        self.order = order


class NavalRole:
    ADMIN = _RoleProxy(999, "ADMIN", "Admin")
    BOT_COMMANDER = _RoleProxy(100, "BOT_COMMANDER", "Bot Commander")
    VOICE = _RoleProxy(1, "VOICE", "Voice")

    def __init__(self, server_id: str):
        self.server_id = server_id

    async def load_role(self, rl: _RoleProxy):
        """
        Loads a role name, allowing for DB name overrides.
        """
        got = await db.get_config(self.server_id, "role:{}".format(rl.name.lower()), default=rl.val)
        return got


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
            elif kwargs["argcount"] == "+":
                self._args_type = 2
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

    async def help(self, server: discord.Server) -> str:
        """
        Get the help for a specific function.
        """
        # load it from locale

        loc = await db.get_config(server.id, "lang", default=None)
        loc = get_locale(loc)

        doc = loc.get("help.{}".format(self._wrapped_coro.__name__))
        if not doc:
            doc = loc["help.None"]

        return doc

    async def _construct_arg_error_msg(self, server: discord.Server):
        prefix = await db.get_config(server.id, "command_prefix", default="?")
        base = """```{}({})""".format(prefix, '|'.join(self.names))

        if self._args_type == 0:
            base += " <1 or more arguments>\n\n"
        elif self._args_type == 1:
            base += " <{} arguments>\n\n".format(self._args_count)

        base += await self.help(server) + "\n```"

        return base

    async def invoke(self, client: discord.Client, message: discord.Message):
        """
        Invoke the function.
        """
        # Set up the role loader.
        role_loader = NavalRole(message.server.id)

        # Load the prefix, again.
        # This is so spaces in prefixes don't break everything.
        prefix = await db.get_config(message.server.id, "command_prefix", default="?")

        # Load the locale loader.
        loc = await db.get_config(message.server.id, "lang", default=None)
        loc = get_locale(loc)

        # Do the checks before running the coroutine.
        # Owner check.

        if self._only_owner:
            owner = util.get_global_config("RCE_ID", default=0, type_=int)
            u_id = int(message.author.id)
            # Check if it is in the ids specified.
            if not u_id == owner:
                #await client.send_message(message.channel, ":no_entry: This command is restricted to bot owners.")
                await client.send_message(message.channel, loc["perms.not_owner"])
                return
        # Role check.

        # Get the user's roles.
        if hasattr(self, "_roles"):
            allowed_roles = self._roles
            try:
                assert isinstance(message.author, discord.Member)
            except AssertionError:
                await client.send_message(message.channel, loc["perms.cannot_determine_role"])
                return

            # Load roles correctly.
            new_roles = set()
            for role in allowed_roles:
                assert isinstance(role, _RoleProxy), "Role should be a NavalRole member in {}".format(
                    self._wrapped_coro.__name__)
                rn = await role_loader.load_role(role)
                new_roles.add(rn)

            if not await has_permissions_with_override(message.author, new_roles, message.server.id,
                                                       self._wrapped_coro.__name__):
                #await client.send_message(
                #    message.channel,
                #    ":no_entry: You do not have any of the required roles: `{}`!"
                #        .format({role.val for role in allowed_roles})
                ss = loc['perms.bad_role'].format(roles={role for role in new_roles})
                await client.send_message(message.channel, ss)
                return

        # Arguments check.
        if hasattr(self, "_args_type"):
            if self._args_type in [0, 2]:
                # Get the content, with the content split.

                ctt = message.content[len(prefix):]

                # Split out the args into a list.
                try:
                    args = shlex.split(ctt)[1:]
                except ValueError:
                    args = ctt.split(" ")[1:]
                if self._args_type == 0 and len(args) < 1:
                    await client.send_message(message.channel, await self._construct_arg_error_msg(message.server))
                    return
            elif self._args_type == 1:
                ctt = message.content[len(prefix):]
                args = shlex.split(ctt)[1:]
                if len(args) != self._args_count:
                    await client.send_message(message.channel, await self._construct_arg_error_msg(message.server))
                    return
        # Create the context.
        ctx = CommandContext(client, message, locale=loc)

        # Now that we've gotten all of the returns out of the way, invoke the coroutine.
        if hasattr(self, "_args_type"):
            ctx.args = args

        result = await self._wrapped_coro(ctx)

        if result:
            await client.send_message(message.channel, result)
