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

import asyncio
import datetime
import hashlib
import logging
import mimetypes
import os
import shutil
import time
import typing
from concurrent import futures
from math import floor
import functools
import re

import aiohttp
import aioredis
import discord

from navalbot.api import db
from navalbot.api import botcls

startup = datetime.datetime.fromtimestamp(time.time())

# Some useful variables
msgcount = 0

loop = asyncio.get_event_loop()

threaded = futures.ThreadPoolExecutor()

# Declare redis pool
redis_pool = None

# Load config.
if not os.path.exists("config.yml"):
    shutil.copyfile("config.example.yml", "config.yml")

logger = logging.getLogger("NavalBot")


async def with_threading(func):
    """
    Runs a func inside a Threaded executor.
    """
    return await loop.run_in_executor(threaded, func)


def format_timedelta(value, time_format="{days} days, {hours2}:{minutes2}:{seconds2}"):
    if hasattr(value, 'seconds'):
        seconds = value.seconds + value.days * 24 * 3600
    else:
        seconds = int(value)

    seconds_total = seconds

    minutes = int(floor(seconds / 60))
    minutes_total = minutes
    seconds -= minutes * 60

    hours = int(floor(minutes / 60))
    hours_total = hours
    minutes -= hours * 60

    days = int(floor(hours / 24))
    days_total = days
    hours -= days * 24

    years = int(floor(days / 365))
    years_total = years
    days -= years * 365

    return time_format.format(**{
        'seconds': seconds,
        'seconds2': str(seconds).zfill(2),
        'minutes': minutes,
        'minutes2': str(minutes).zfill(2),
        'hours': hours,
        'hours2': str(hours).zfill(2),
        'days': days,
        'years': years,
        'seconds_total': seconds_total,
        'minutes_total': minutes_total,
        'hours_total': hours_total,
        'days_total': days_total,
        'years_total': years_total,
    })


async def get_pool() -> aioredis.RedisPool:
    """
    Gets the redis connection pool.
    """
    global redis_pool
    global_config = botcls.NavalClient.get_navalbot().config
    if not redis_pool:
        redis_pool = await aioredis.create_pool(
            (global_config["redis"]["ip"], global_config["redis"]["port"]),
            db=int(global_config["redis"].get("db", 0)),
            password=global_config["redis"].get("password")
        )
    return redis_pool


def has_permissions(author: discord.Member, roles: set):
    U_roles = set([r.name for r in author.roles])
    if roles.intersection(U_roles):
        return True
    else:
        return False


async def has_permissions_with_override(author: discord.Member, roles: set,
                                        serv_id: int, cmd_name: str):
    allowed = await _get_overrides(serv_id, cmd_name)

    allowed = roles.union(allowed)

    return has_permissions(author, allowed)


async def _get_overrides(serv_id: int, cmd_name: str) -> set:
    async with (await get_pool()).get() as conn:
        assert isinstance(conn, aioredis.Redis)
        override = await conn.smembers("override:{}:{}".format(serv_id, cmd_name))
        if override:
            override = {_.decode() for _ in override}
        else:
            override = set()

    return override


async def get_prefix(id: str) -> str:
    """
    Gets the command prefix of the server specified.
    """
    return await db.get_config(id, "command_prefix", default="?")


def prov_dec_func(func1, func2):
    """
    Provides a decorated function with the right chains.

    Func is the original func, func2 is the fake func.
    """

    func2.__doc__ = func1.__doc__
    func2.__name__ = func1.__name__

    if hasattr(func1, "__methods"):
        func2.__methods = func1.__methods
    else:
        func2.__methods = {}

    if hasattr(func1, "func"):
        # chain the .func call for source function
        func2.func = func1.func
    else:
        func2.func = func1

    return func2


def get_global_config(key, default=0, type_: type = None):
    global_config = botcls.NavalClient.get_navalbot().config
    if type_ is not None:
        return type_(global_config.get(key, default))
    else:
        return global_config.get(key, default)


async def get_file(client: tuple, url, name):
    """
    Get a file from the web using aiohttp, and save it
    """
    with aiohttp.ClientSession() as sess:
        async with sess.get(url) as get:
            assert isinstance(get, aiohttp.ClientResponse)
            if int(get.headers["content-length"]) > 1024 * 1024 * 8:
                # 1gib
                await client[0].send_message(client[1].channel, "File {} is too big to DL".format(name))
                return
            else:
                data = await get.read()
                with open(os.path.join(os.getcwd(), 'files', name), 'wb') as f:
                    f.write(data)
                print("--> Saved file to {}".format(name))


async def get_image(url: str) -> typing.Union[str, None]:
    """
    Get an image if the mime type says it's an image, otherwise return None.

    Then, return the file name with the appropriate extension.
    """
    with aiohttp.ClientSession() as sess:
        async with sess.head(url) as hh:
            assert isinstance(hh, aiohttp.ClientResponse)
            if "image" not in hh.headers.get("Content-Type", ""):
                # Not an image, return.
                return

        # Get the image.
        async with sess.get(url) as got:
            assert isinstance(got, aiohttp.ClientResponse)
            # Don't download big files.
            if int(got.headers["content-length"]) > 1024 * 1024 * 8:
                return None
            # Generate the file name using the hash of the URL.
            name = hashlib.sha224(url.encode()).hexdigest()
            # Guess the extension.
            ext = mimetypes.guess_extension(got.headers.get("Content-Type", ""))
            if ext == ".jpe":
                # .jpe is bad
                ext = ".jpg"
            if not ext:
                # AAAA what
                # Skip the file.
                return
            # Create the final file name.
            final = name + ext
            # Download the file.
            with open(os.path.join(os.getcwd(), 'files', final), 'wb') as f:
                f.write(await got.read())
            # Return the name.
            return final


def sanitize(param):
    # Strip out `/` from the path to prevent transversal through directories.
    ret = ''.join([c for c in param if c.isalnum() or c in [".", "_"]])
    return ret


async def with_cache(data, expires=300, miss=lambda data: None):
    """
    Caches the result of a function.
    """
    pool = await get_pool()
    async with pool.get() as conn:
        # Get the cached key.
        content = await conn.get("cached:{}".format(data))
        if content:
            logger.info("Cache hit for {}.".format(data))
            return content.decode()
        logger.info("Cache miss for {}.".format(data))
        # Call miss(data), and set the data in the cache.
        result = await miss(data)
        await conn.set("cached:{}".format(data), result)
        await conn.expire("cached:{}".format(data), expires)
        return result


def has_perm(perms: discord.Permissions, attr: str) -> bool:
    if perms.administrator:
        return True
    if getattr(perms, attr, False):
        return True
    return False


@functools.lru_cache(maxsize=None)
def get_regex(reg: str):
    """
    Returns a compiled regular expression.
    """
    return re.compile(reg)
