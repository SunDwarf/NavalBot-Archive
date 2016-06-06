# -*- coding: utf-8 -*-
"""
The main file wrapper for NavalBot.

This invokes `bot.run()`.

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
import os
import sys
from ctypes.util import find_library

import discord
import requests

# Load config.
import shutil
import yaml

from navalbot.api import botcls

if not os.path.exists("config.yml"):
    shutil.copyfile("config.example.yml", "config.yml")

with open("config.yml", "r") as f:
    global_config = yaml.load(f)

if global_config.get("use_libuv", False):
    print("WARNING: Using libuv faster event loop for NavalBot.")
    print("Voice modules will not work properly.")
    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

# Load opus
if sys.platform == "win32":
    if os.path.exists(os.path.join(os.getcwd(), "libopus.dll")):
        found = "libopus"
    else:
        found = False
    has_setproctitle = False

else:
    found = find_library("opus")
    has_setproctitle = True
    import setproctitle
if found:
    print(">> Loaded libopus from {}".format(found))
    discord.opus.load_opus(found)
else:
    if sys.platform == "win32":
        print(">> Downloading libopus for Windows.")
        sfbit = sys.maxsize > 2 ** 32
        if sfbit:
            to_dl = 'x64'
        else:
            to_dl = 'x86'
        r = requests.get("https://github.com/SexualRhinoceros/MusicBot/raw/develop/libopus-0.{}.dll".format(to_dl),
                         stream=True)
        # Save it as libopus.dll
        with open("libopus.dll", 'wb') as f:
            for chunk in r.iter_content(256):
                f.write(chunk)
        discord.opus.load_opus("libopus")
        del sfbit, to_dl
    else:
        print(">> Cannot load opus library - cannot use voice.")
        del found

# Create a client.
# Also, use shards as appropriate.
if global_config.get("shards", {}).get("enable_sharding"):
    # Todo -> Auto shards
    shards = global_config["shards"]["shard_max"]
    my_shard = global_config["shards"]["shard_id"]
    client = botcls.NavalClient(shard_count=int(shards), shard_id=int(my_shard))
else:
    client = botcls.NavalClient()

# Update process title.
if has_setproctitle:
    setproctitle.setproctitle("NavalBot - {bot_id}".format(
        bot_id=global_config.get("client", {}).get("oauth_client_id", "???"))
    )

# Invoke bot.run().
if __name__ == '__main__':
    client.navalbot()
