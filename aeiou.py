import os
import traceback
import sys

import discord
from discord import Client

import commands

client = Client()

COMMAND_PREFIX = "?"

VERSION = "1.0.5"
VERSIONT = tuple(int(i) for i in VERSION.split("."))

# Methods
@client.event
async def on_ready():
    # print ready msg
    print("Loaded NavalBot, logged in as `{}`.".format(client.user.name))
    # run ready CB
    await commands.on_ready(client)
    # make file dir
    try:
        os.makedirs(os.path.join(os.getcwd(), "files"))
    except FileExistsError:
        pass


@client.event
async def on_message(message: discord.Message):
    print("-> Recieved message:", message.content, "from", message.author.name)
    # Check if it matches the command prefix.
    if message.author.name == "NavalBot":
        print("--> Not processing own message")
        return
    if message.content[0] == COMMAND_PREFIX:
        try:
            coro = getattr(commands, message.content[1:].split(' ')[0])(client, message)
        except AttributeError as e:
            print("-> No such command:", e)
            coro = commands.default(client, message)
        try:
            await coro
        except Exception as e:
            if isinstance(e, discord.HTTPException):
                pass
            else:
                await client.send_message(message.channel, content="```\n{}\n```".format(traceback.format_exc()))


if __name__ == "__main__":
    client.run(sys.argv[1], sys.argv[2])
