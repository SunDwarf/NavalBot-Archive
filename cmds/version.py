import re

import aiohttp
import discord

# =============== Commands
import cmds
from bot import VERSION, VERSIONT


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
    """
    Checks for the latest stable version of NavalBot.
    """
    await client.send_message(
        message.channel,
        "Version **{}**, written by SunDwarf (https://github.com/SunDwarf) and shadow (https://github.com/ilevn)"
            .format(VERSION)
    )
    # Download the latest version
    async with aiohttp.ClientSession() as sess:
        s = await sess.get("https://raw.githubusercontent.com/SunDwarf/NavalBot/stable/bot.py")
        assert isinstance(s, aiohttp.ClientResponse)
        data = await s.read()
        data = data.decode().split('\n')
    version = read_version(data)
    if not version:
        await client.send_message(message.channel, ":grey_exclamation: Could not download version information.")
        return
    if tuple(int(i) for i in version.split(".")) > VERSIONT:
        await client.send_message(message.channel, ":exclamation: *New version available:* **{}**".format(version))
    elif tuple(int(i) for i in version.split(".")) < VERSIONT:
        await client.send_message(message.channel, ":grey_exclamation: *You are running a newer version than the one "
                                                   "available online ({}).*".format(version))
    else:
        await client.send_message(message.channel, ":grey_exclamation: *You are running the latest version.*")
