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
import shlex

import discord

from navalbot.api.util import has_permissions_with_override, _get_overrides, prov_dec_func, get_global_config


def with_permission(*role: str):
    """
    Only allows a command with permission.
    """
    role = set(role)

    def __decorator(func):
        async def __fake_func(client: discord.Client, message: discord.Message):
            # Get the user's roles.
            try:
                assert isinstance(message.author, discord.Member)
            except AssertionError:
                await client.send_message(message.channel, ":no_entry: Cannot determine your role!")
                return

            # Use has_permissions with override.
            if await has_permissions_with_override(message.author, role, message.server.id, func.__name__) \
                    or message.author == message.server.owner:
                await func(client, message)
            else:
                await client.send_message(message.channel,
                                          ":no_entry: You do not have any of the required roles: `{}`!".format(role))

        async def __get_roles(server_id):
            return role.union(await _get_overrides(server_id, func.__name__))

        # Wrap func
        __fake_func = prov_dec_func(func, __fake_func)

        __fake_func.__methods["get_roles"] = __get_roles

        return __fake_func

    return __decorator


def enforce_args(count: int, error_msg: str = None):
    """
    Ensure a command has been passed a certain amount of arguments.
    """
    if not error_msg:
        error_msg = (":x: Not enough arguments provided! You must provide at least `{}` args! "
                     "You can have spaces in these arguments by surrounding them in `\"\"`.".format(count))
    else:
        error_msg = error_msg.format(max_count=count)

    def __decorator(func):
        async def __fake_enforcing_func(client: discord.Client, message: discord.Message):
            # Check the number of args.
            try:
                split = shlex.split(message.content)
                # Remove the `command` from the front.
                split.pop(0)
                if len(split) < count:
                    await client.send_message(
                        message.channel,
                        error_msg
                    )
                    return
                else:
                    # Await the function.
                    await func(client, message, split)

            except ValueError:
                await client.send_message(message.channel, ":x: You must escape your quotation marks: `\\'`")

        __fake_enforcing_func = prov_dec_func(func, __fake_enforcing_func)

        return __fake_enforcing_func

    return __decorator


def owner(func):
    """
    Only allows owner to run the command.
    """

    owner = util.get_global_config("RCE_ID", default=0, type_=int)

    async def __fake_permission_func(client: discord.Client, message: discord.Message):
        # Get the ID.
        u_id = int(message.author.id)
        # Check if it is in the ids specified.
        if u_id == owner:
            await func(client, message)
        else:
            await client.send_message(message.channel,
                                      ":no_entry: This command is restricted to bot owners!")

    __fake_permission_func = prov_dec_func(func, __fake_permission_func)

    return __fake_permission_func