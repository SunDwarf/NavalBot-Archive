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

# Hooks file.
# This allows adding hooks to `on_message`, and generic events.
import logging
import types
import typing

import discord

from navalbot.api.botcls import NavalClient

logger = logging.getLogger("NavalBot")


def on_message(func: typing.Callable[[NavalClient, discord.Message], None]) -> types.FunctionType:
    """
    Registers a hook to be ran every message.
    """
    try:
        instance = NavalClient.instance
        assert isinstance(instance, NavalClient)
    except (AssertionError, AttributeError):
        logger.critical("Attempted to register on_message for function `{}` before bot is created."
                        .format(func.__name__))
        return

    if 'on_message' not in instance.hooks:
        instance.hooks["on_message"] = []

    instance.hooks["on_message"].append(func)


def on_generic_event(func: typing.Callable[[NavalClient, dict], None]) -> types.FunctionType:
    """
    Registers a hook to be ran on every event.
    """
    try:
        instance = NavalClient.instance
        assert isinstance(instance, NavalClient)
    except (AssertionError, AttributeError):
        logger.critical("Attempted to register on_message for function `{}` before bot is created."
                        .format(func.__name__))
        return

    if 'on_recv' not in instance.hooks:
        instance.hooks['on_recv'] = []

    instance.hooks['on_recv'].append(func)
