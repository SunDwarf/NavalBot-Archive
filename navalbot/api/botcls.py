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

# Subclass of discord.Client.
import importlib
import json
import os
import logging
import traceback
import shutil
import sys
import time

import yaml
import discord
from raven import Client
from raven_aiohttp import AioHttpTransport

from navalbot import builtins
from navalbot.api import db
from navalbot.api.commands import commands, Command
from navalbot.api import util

logger = logging.getLogger("NavalBot")


class NavalClient(discord.Client):
    """
    An overridden discord Client.
    """
    instance = None

    @classmethod
    def init_logging(cls):
        if sys.platform == "win32":
            logging.basicConfig(filename='nul', level=logging.INFO)
        else:
            logging.basicConfig(filename='/dev/null', level=logging.INFO)

        formatter = logging.Formatter('%(asctime)s - [%(levelname)s] %(name)s -> %(message)s')
        root = logging.getLogger()

        consoleHandler = logging.StreamHandler()
        consoleHandler.setFormatter(formatter)
        root.addHandler(consoleHandler)

    def __new__(cls, *args, **kwargs):
        """
        Singleton class
        """
        if not cls.instance:
            cls.init_logging()
            cls.instance = super().__new__(cls, *args)
        return cls.instance

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.modules = {}

        if not os.path.exists("config.yml"):
            shutil.copyfile("config.example.yml", "config.yml")

        with open("config.yml", "r") as f:
            self.config = yaml.load(f)

        # Pre-load the blacklist.
        if os.path.exists("blacklist.json"):
            with open("blacklist.json") as f:
                self.bl = json.load(f)
                self.bl_mtime = os.stat(f.fileno()).st_mtime
        else:
            self.bl = []
            self.bl_mtime = time.time()

        # Create a client if the config says so.
        if self.config.get("use_sentry"):
            logger.info("Using Sentry for error reporting.")
            self._raven_client = Client(dsn=self.config.get("sentry_dsn"), transport=AioHttpTransport)
        else:
            self._raven_client = None

    async def on_error(self, event_method, *args, **kwargs):
        """
        Send the error to Sentry if applicable.

        Otherwise, just traceback it.
        """
        if self._raven_client:
            self._raven_client.captureException()
        else:
            logger.error("Caught error in {}".format(event_method))
            traceback.print_exc()

    def load_plugins(self):
        """
        Loads plugins from plugins/.
        """
        if not os.path.exists(os.path.join(os.getcwd(), "plugins/")):
            logger.critical("No plugins directory exists. Your bot is effectively useless.")
            return
        # Loop over things in plugins/
        for entry in os.scandir("plugins/"):
            if entry.name == "__pycache__" or entry.name == "__init__.py":
                continue
            if entry.name.endswith(".py"):
                name = entry.name.split(".")[0]
            else:
                if os.path.isdir(entry.path) or os.path.islink(entry.path):
                    name = entry.name
                else:
                    continue
            import_name = "plugins." + name
            # Import using importlib.
            try:
                mod = importlib.import_module(import_name)
                if hasattr(mod, "load_plugin"):
                    mod.load_plugin(self)
                self.modules[mod.__name__] = mod
                logger.info("Loaded plugin {} (from {})".format(mod.__name__, mod.__file__))
            except Exception as e:
                logger.error("Error upon loading plugin `{}`! Cannot continue loading.".format(import_name))
                traceback.print_exc()
                return

    async def on_ready(self):
        # Get the OAuth2 URL, or something
        if self.user.bot:
            bot_id = self.config.get("client", {}).get("oauth_client_id")
            permissions = discord.Permissions.all_channel()
            oauth_url = discord.utils.oauth_url(str(bot_id), permissions=permissions)
            if bot_id is None:
                logger.critical("You didn't set the bot ID in config.yml. Your bot cannot be invited anywhere.")
                sys.exit(1)
            logger.info("NavalBot is now using OAuth2, OAuth URL: {}".format(oauth_url))
        else:
            logger.warning("NavalBot is still using a legacy account. This will stop working soon!")

        # print ready msg
        logger.info("Loaded NavalBot, logged in as `{}`.".format(self.user.name))
        # make file dir
        try:
            os.makedirs(os.path.join(os.getcwd(), "files"))
        except FileExistsError:
            pass

        # Load plugins
        self.load_plugins()

        # Set the game.
        await self.change_status(discord.Game(name="Type ?info for help!"))

    async def on_message(self, message: discord.Message):
        # Increment the message count.
        util.msgcount += 1

        if not isinstance(message.channel, discord.PrivateChannel):
            # print(Fore.RED + message.server.name, ":", Fore.GREEN + message.channel.name, ":",
            #      Fore.CYAN + message.author.name , ":", Fore.RESET + message.content)
            logger.info("Recieved message: {message.content} from {message.author.name}".format(message=message))
            logger.info(" On channel: #{message.channel.name}".format(message=message))

        # Check if it matches the command prefix.
        if message.author.id == self.user.id:
            logger.info("Not processing own message.")
            return

        # Re-process the blacklist.
        if os.path.exists("blacklist.json"):
            # Get the time
            mtime = os.stat("blacklist.json").st_mtime
            if mtime > self.bl_mtime:
                logger.debug("Blacklist file changed, reloading...")
                # Update mtime
                self.bl_mtime = mtime
                # Reload blacklist
                with open("blacklist.json") as f:
                    self.bl = json.load(f)

        # Check for a valid server.
        if message.server is not None:
            prefix = await db.get_config(message.server.id, "command_prefix", "?")
            autodelete = True if await db.get_config(message.server.id, "autodelete") == "True" else False
            if autodelete and message.content.startswith(prefix):
                await self.delete_message(message)
            logger.info(" On server: {} ({})".format(message.server.name, message.server.id))
        else:
            # No DMs
            await self.send_message(message.channel, "I don't accept private messages.")
            return

        if message.server.id in self.bl:
            bb = self.bl[message.server.id]
            if message.author.id in bb:
                # Ignore message
                logger.warn("Ignoring message, as user is on the blacklist.")
                return


        if len(message.content) == 0:
            logger.info("Ignoring (presumably) image-only message.")
            return

        # Run on_message hooks
        # for hook in cmds.message_hooks.values():
        #    logger.info("Running hook {}".format(hook.__name__))
        #    try:
        #        await hook(client, message)
        #    except StopProcessing:
        #        return

        if message.content.startswith(prefix):
            cmd_content = message.content[len(prefix):]
            cmd_word = cmd_content.split(" ")[0].lower()
            try:
                coro = commands[cmd_word]
            except KeyError as e:
                logger.warning("-> No such command: " + str(e))
                coro = builtins.default
            try:
                if isinstance(coro, Command):
                    await coro.invoke(self, message)
                else:
                    await coro(self, message)
            except Exception as e:
                await self.send_message(message.channel, content="```\n{}\n```".format(traceback.format_exc()))
                # Allow it to fall through.
                raise

    def navalbot(self):
        # Switch login method based on args.
        use_oauth = self.config.get("client", {}).get("use_oauth", False)
        if use_oauth:
            login = (self.config.get("client", {}).get("oauth_bot_token", ""),)
        else:
            login = (self.config.get("client", {}).get("old_bot_user", "lol"),
                     self.config.get("client", {}).get("old_bot_pw", "aaaa"))
        try:
            self.loop.run_until_complete(self.login(*login))
        except discord.errors.HTTPException as e:
            if e.response.status == 401:
                logger.error("Your bot token is incorrect. Cannot login.")
                return
            else:
                raise

        while True:
            try:
                self.loop.run_until_complete(self.connect())
            except KeyboardInterrupt:
                try:
                    self.loop.run_until_complete(self.logout())
                except Exception:
                    logger.error("Couldn't log out. Oh well. We tried!")
                    return
                return
            except RuntimeError:
                logger.error("Session appears to have errored. Exiting.")
                return
            except Exception:
                traceback.print_exc()
                logger.error("Crashed. Don't know how, don't care. Continuing..")
                continue
