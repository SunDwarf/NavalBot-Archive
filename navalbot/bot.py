# -*- coding: utf-8 -*-
"""
The main entry point of NavalBot.

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
import json
import logging
import os
import re
import sys
import time

import discord
# =============== Commands
import cmds
from navalbot.api import util, db
from cmds import commands

from exceptions import StopProcessing

# =============== End commands

loop = asyncio.get_event_loop()

# ===============

# Define logging.

def init_logging():
    if sys.platform == "win32":
        logging.basicConfig(filename='nul', level=logging.INFO)
    else:
        logging.basicConfig(filename='/dev/null', level=logging.INFO)

    formatter = logging.Formatter('%(asctime)s - [%(levelname)s] %(name)s -> %(message)s')
    root = logging.getLogger()

    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(formatter)
    root.addHandler(consoleHandler)


logger = logging.getLogger("NavalBot")
logger.setLevel(logging.DEBUG)


# Factoid matcher compiled
factoid_matcher = re.compile(r'(\S*?) is (.*)')

# Pre-load the blacklist.
if os.path.exists("blacklist.json"):
    with open("blacklist.json") as f:
        bl = json.load(f)
        bl_mtime = os.stat(f.fileno()).st_mtime
else:
    bl = []
    bl_mtime = time.time()


def load_plugins():
    """
    Loads plugins from plugins/.
    """



# ============= Built-in commands.


# endregion

def run(client, config):
    """
    The main running point.
    """
    # Base events.
    @client.event
    async def on_ready():
        # Get the OAuth2 URL, or something
        if client.user.bot:
            bot_id = config.get("client", {}).get("oauth_client_id")
            permissions = discord.Permissions.all_channel()
            oauth_url = discord.utils.oauth_url(str(bot_id), permissions=permissions)
            if bot_id is None:
                logger.critical("You didn't set the bot ID in config.yml. Your bot cannot be invited anywhere.")
                sys.exit(1)
            logger.info("NavalBot is now using OAuth2, OAuth URL: {}".format(oauth_url))
        else:
            logger.warning("NavalBot is still using a legacy account. This will stop working soon!")

        # Change voice module as applicable.
        from voice import voice_main as voice
        # print ready msg
        logger.info("Loaded NavalBot, logged in as `{}`.".format(client.user.name))
        # make file dir
        try:
            os.makedirs(os.path.join(os.getcwd(), "files"))
        except FileExistsError:
            pass
        # load the voice handler
        if hasattr(voice, "play_music_from_queue"):
            logger.warning("Using old queue-based music player!")
            loop.create_task(voice.play_music_from_queue())

        # Set the game.
        await client.change_status(discord.Game(name="Type ?info for help!"))

    @client.event
    async def on_message(message: discord.Message):
        # Increment the message count.
        util.msgcount += 1

        if not isinstance(message.channel, discord.PrivateChannel):
            # print(Fore.RED + message.server.name, ":", Fore.GREEN + message.channel.name, ":",
            #      Fore.CYAN + message.author.name , ":", Fore.RESET + message.content)
            logger.info("Recieved message: {message.content} from {message.author.name}".format(message=message))
            logger.info(" On channel: #{message.channel.name}".format(message=message))

        # Check if it matches the command prefix.
        if message.author.id == client.user.id:
            logger.info("Not processing own message.")
            return

        # Re-process the blacklist.
        if os.path.exists("blacklist.json"):
            # Get the time
            mtime = os.stat("blacklist.json").st_mtime
            if mtime > bl_mtime:
                logger.debug("Blacklist file changed, reloading...")
                # Update mtime
                global bl_mtime
                bl_mtime = mtime
                # Reload blacklist
                with open("blacklist.json") as f:
                    global bl
                    bl = json.load(f)

        if message.server.id in bl:
            bb = bl[message.server.id]
            if message.author.id in bb:
                # Ignore message
                logger.warn("Ignoring message, as user is on the blacklist.")
                return

        # Check for a valid server.
        if message.server is not None:
            prefix = await db.get_config(message.server.id, "command_prefix", "?")
            autodelete = True if await db.get_config(message.server.id, "autodelete") == "True" else False
            if autodelete and message.content.startswith(prefix):
                await client.delete_message(message)
            logger.info(" On server: {} ({})".format(message.server.name, message.server.id))
        else:
            # No DMs
            await client.send_message(message.channel, "I don't accept private messages.")
            return

        if len(message.content) == 0:
            logger.info("Ignoring (presumably) image-only message.")
            return

        # Run on_message hooks
        for hook in cmds.message_hooks.values():
            logger.info("Running hook {}".format(hook.__name__))
            try:
                await hook(client, message)
            except StopProcessing:
                return

        if message.content.startswith(prefix):
            cmd_content = message.content[len(prefix):]
            cmd_word = cmd_content.split(" ")[0].lower()
            try:
                coro = commands[cmd_word](client, message)
            except KeyError as e:
                logger.warning("-> No such command: " + str(e))
                coro = default(client=client, message=message)
            try:
                await coro
            except Exception as e:
                await client.send_message(message.channel, content="```\n{}\n```".format(traceback.format_exc()))

    init_logging()
    # Switch login method based on args.
    use_oauth = config.get("client", {}).get("use_oauth", False)
    if use_oauth:
        login = (config.get("client", {}).get("oauth_bot_token", ""),)
    else:
        login = (config.get("client", {}).get("old_bot_user", "lol"),
                 config.get("client", {}).get("old_bot_pw", "aaaa"))
    try:
        loop.run_until_complete(client.login(*login))
    except discord.errors.HTTPException as e:
        if e.response.status == 401:
            logger.error("Your bot token is incorrect. Cannot login.")
            return
        else:
            raise

    while True:
        try:
            loop.run_until_complete(client.connect())
        except KeyboardInterrupt:
            try:
                loop.run_until_complete(client.logout())
            except Exception:
                logger.error("Couldn't log out. Oh well. We tried!")
                return
            return
        except RuntimeError:
            logger.error("Session appears to have errored. Exiting.")
            return
        except Exception:
            import traceback
            traceback.print_exc()
            logger.error("Crashed. Don't know how, don't care. Continuing..")
            continue


if __name__ == "__main__":
    print("Deprecated - use main.py")
    raise SystemExit()