import asyncio
import os
import re
import sqlite3
import sys
import traceback

from ctypes.util import find_library

import cmds.ndc

import aiohttp
import discord
from discord import Client

# =============== Commands
import cmds
from cmds import commands
# Fuck off PyCharm
import importlib

importlib.import_module("cmds.cfg")
importlib.import_module("cmds.fun")
importlib.import_module("cmds.moderation")
importlib.import_module("cmds.ndc")
importlib.import_module("cmds.voice")

# =============== End commands

# Load opus
discord.opus.load_opus(find_library("opus"))

# Create a client.
client = Client()

# Define the command prefix.
COMMAND_PREFIX = os.environ.get("NAVALBOT_CMD_PREFIX", "?")

# Version information.
VERSION = "1.1.2"
VERSIONT = tuple(int(i) for i in VERSION.split("."))

# Factoid matcher compiled
factoid_matcher = re.compile(r'(.*?) is (.*)')

# Get DB
db = sqlite3.connect("navalbot.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS factoids (
  id INTEGER PRIMARY KEY, name VARCHAR, content VARCHAR, locked INTEGER, locker VARCHAR
);
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS configuration (
  id INTEGER PRIMARY KEY,
  name VARCHAR,
  value VARCHAR
)
""")

loop = asyncio.get_event_loop()

attrdict = type("AttrDict", (dict,), {"__getattr__": dict.__getitem__, "__setattr__": dict.__setitem__})


# Events.
@client.event
async def on_ready():
    # print ready msg
    print("Loaded NavalBot, logged in as `{}`.".format(client.user.name))
    # make file dir
    try:
        os.makedirs(os.path.join(os.getcwd(), "files"))
    except FileExistsError:
        pass
    # Set the current game, as saved.
    cursor.execute("SELECT (value) FROM configuration WHERE configuration.name = 'game'")
    result = cursor.fetchone()
    if not result:
        # Ignore.
        return
    else:
        game = result[0]
        await client.change_status(game=discord.Game(name=game))


@client.event
async def on_message(message: discord.Message):
    print("-> Recieved message:", message.content, "from", message.author.name)
    print("--> On channel: #" + message.channel.name)
    # Check if it matches the command prefix.
    if message.author.name == "NavalBot":
        print("--> Not processing own message")
        return
    if message.content[0] == COMMAND_PREFIX:
        try:
            coro = commands[message.content[1:].split(' ')[0]](client, message)
        except KeyError as e:
            print("-> No such command:", e)
            coro = default(client=client, message=message)
        try:
            await coro
        except Exception as e:
            if isinstance(e, discord.HTTPException):
                pass
            else:
                await client.send_message(message.channel, content="```\n{}\n```".format(traceback.format_exc()))


# ============= Built-in commands.

def read_version(data):
    regexp = re.compile(r"^VERSION\W*=\W*([\d.abrc]+)")

    for line in data:
        match = regexp.match(line)
        if match is not None:
            return match.group(1)
    else:
        print("Cannot get new version from GitHub.")


@cmds.command("version")
async def version(client: discord.Client, message: discord.Message):
    await client.send_message(
        message.channel,
        "Version **{}**, written by SunDwarf (https://github.com/SunDwarf) and shadow (https://github.com/ilevn)"
            .format(VERSION)
    )
    # Download the latest version
    async with aiohttp.ClientSession() as sess:
        s = await sess.get("https://raw.githubusercontent.com/SunDwarf/NavalBot/master/bot.py")
        assert isinstance(s, aiohttp.ClientResponse)
        data = await s.read()
        data = data.decode().split('\n')
    version = read_version(data)
    if not version:
        await client.send_message(message.channel, ":grey_exclamation: Could not download version information.")
        return
    if tuple(int(i) for i in version.split(".")) > VERSIONT:
        await client.send_message(message.channel, ":exclamation: *New version available:* **{}**".format(version))
    else:
        await client.send_message(message.channel, ":grey_exclamation: *You are running the latest version.*")


async def get_file(client: tuple, url, name):
    """
    Get a file from the web using aiohttp, and save it
    """
    with aiohttp.ClientSession() as sess:
        async with sess.get(url) as get:
            assert isinstance(get, aiohttp.ClientResponse)
            if int(get.headers["content-length"]) > 1024 * 1024 * 8:
                # 1gib
                await client[0].send_message(client[1].channel, "File {} is too big to DL")
                return
            else:
                data = await get.read()
                with open(os.path.join(os.getcwd(), 'files', name), 'wb') as f:
                    f.write(data)
                print("--> Saved file to {}".format(name))


def sanitize(param):
    param = param.replace('..', '.').replace('/', '')
    param = param.split('?')[0]
    return param


async def default(client: discord.Client, message: discord.Message):
    data = message.content[1:]
    # Check if it matches a factoid creation
    matches = factoid_matcher.match(data)
    if matches:
        # Set the factoid
        name = matches.groups()[0]
        fac = matches.groups()[1]
        assert isinstance(fac, str)
        if fac.startswith("http") and 'youtube' not in fac:
            # download as a file
            file = sanitize(fac.split('/')[-1])
            client.loop.create_task(get_file((client, message), url=fac, name=file))
            fac = "file:{}".format(file)
        # check if locked
        cursor.execute("SELECT locked, locker FROM factoids WHERE factoids.name = ?", (name,))
        row = cursor.fetchone()
        if row:
            locked, locker = row
            if locked and locker != message.author.id and int(message.author.id) not in cmds.ndc.RCE_IDS:
                await client.send_message(message.channel, "Cannot change factoid `{}` locked by `{}`"
                                          .format(name, locker))
                return
        cursor.execute("INSERT OR REPLACE "
                       "INTO factoids (id, name, content) "
                       "VALUES ((SELECT id FROM factoids WHERE name = ?), ?, ?)", (name, name, fac))
        db.commit()
        await client.send_message(message.channel, "Factoid `{}` is now `{}`".format(name, fac))
    else:
        # Get factoid
        cursor.execute("SELECT (content) FROM factoids WHERE factoids.name = ?", (data,))
        rows = cursor.fetchone()
        if not rows:
            return
        # Load content
        content = rows[0]
        assert isinstance(content, str)
        # Check if it's a file
        if content.startswith("file:"):
            fname = content.split("file:")[1]
            # if not os.path.exists(os.path.join(os.getcwd(), 'files', fname)):
            #    await client.send_message(message.channel, "This kills the bot")
            #    return
            # Load the file
            with open(os.path.join(os.getcwd(), 'files', fname), 'rb') as f:
                await client.send_file(message.channel, f)
            return
        await client.send_message(message.channel, content)


if __name__ == "__main__":
    client.run(sys.argv[1], sys.argv[2])
