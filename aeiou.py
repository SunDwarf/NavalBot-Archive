import discord
from discord import Client
import commands
import os

import sys

client = Client()

COMMAND_PREFIX = "?"


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
    except FileExistsError: pass


@client.event
async def on_message(message: discord.Message):
    print("-> Recieved message:", message.content, "from", message.author.name)
    # Check if it matches the command prefix.
    if message.author.name == "NavalBot":
        print("--> Not processing own message")
        return
    if message.content[0] == COMMAND_PREFIX:
        try:
            await getattr(commands, message.content[1:].split(' ')[0])(client, message)
        except AttributeError as e:
            print("-> No such command:", e)
            await getattr(commands, "default")(client, message)


if __name__ == "__main__":
    client.run(sys.argv[1], sys.argv[2])
