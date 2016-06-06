"""
New commands package.

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

from .cmdclass import Command
from .ctx import CommandContext

commands = {}
_func_cmd_mapping = {}


# Deprecated. Use @command which is much better.
def oldcommand(*names):
    """
    Register a new basic command.

    This is a single command decorator.
    """

    def __decorator(func):
        for name in names:
            commands[name] = func
        # Update __methods.
        if hasattr(func, "__methods"):
            for k, v in func.__methods.items():
                setattr(func, k, v)
        return func

    return __decorator


def command(*names, **kwargs):
    """
    Register a new command.
    """

    def __decorator(func):
        # Create the class.
        cls = Command(func, *names, **kwargs)
        for name in names:
            commands[name] = cls

        _func_cmd_mapping[func] = cls

        return cls

    return __decorator
