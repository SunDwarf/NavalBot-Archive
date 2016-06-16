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
import asyncio
import copy
import importlib
import json
import logging
import os
import shutil
import sys
import traceback

import aiohttp
import aioredis
import discord
import yaml
from raven import Client
from raven_aiohttp import AioHttpTransport

from navalbot.api import db
from navalbot.api import util
from navalbot.api.contexts import OnMessageEventContext
from navalbot.api.locale import get_locale
from navalbot.api.util import get_pool
from navalbot.voice import voiceclient

logger = logging.getLogger("NavalBot")


class NavalClient(discord.Client):
    """
    An overridden discord Client.
    """
    instance = None

    @classmethod
    def get_navalbot(cls) -> 'NavalClient':
        """
        Get the current instance of the bot.
        """
        return cls.instance

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

    def vc_factory(self):
        """
        Method to return a new voice client class.
        """
        return voiceclient.NavalVoiceClient

    async def join_voice_channel(self, channel):
        """
        Override function for discord.py's join_voice_channel that allows me to specify a class to construct.
        """
        if isinstance(channel, discord.Object):
            channel = self.get_channel(channel.id)

        if getattr(channel, 'type', discord.ChannelType.text) != discord.ChannelType.voice:
            raise discord.InvalidArgument('Channel passed must be a voice channel')

        server = channel.server

        if self.is_voice_connected(server):
            raise discord.ClientException('Already connected to a voice channel in this server')

        logger.info('attempting to join voice channel {0.name}'.format(channel))

        def session_id_found(data):
            user_id = data.get('user_id')
            return user_id == self.user.id

        # register the futures for waiting
        session_id_future = self.ws.wait_for('VOICE_STATE_UPDATE', session_id_found)
        voice_data_future = self.ws.wait_for('VOICE_SERVER_UPDATE', lambda d: True)

        # request joining
        await self.ws.voice_state(server.id, channel.id)
        session_id_data = await asyncio.wait_for(session_id_future, timeout=10.0, loop=self.loop)
        data = await asyncio.wait_for(voice_data_future, timeout=10.0, loop=self.loop)

        kwargs = {
            'user': self.user,
            'channel': channel,
            'data': data,
            'loop': self.loop,
            'session_id': session_id_data.get('session_id'),
            'main_ws': self.ws
        }

        klass = self.vc_factory()

        voice = klass(**kwargs)
        try:
            await voice.connect()
        except asyncio.TimeoutError as e:
            try:
                await voice.disconnect()
            except:
                # we don't care if disconnect failed because connection failed
                pass
            raise e  # re-raise

        self.connection._add_voice_client(server.id, voice)
        return voice

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
        self.hooks = {}

        try:
            config_file = sys.argv[1]
        except IndexError:
            config_file = "config.yml"

        if not os.path.exists(config_file):
            shutil.copyfile("config.example.yml", config_file)

        with open(config_file, "r") as f:
            self.config = yaml.load(f)

        # Create a client if the config says so.
        if self.config.get("use_sentry"):
            logger.info("Using Sentry for error reporting.")
            self._raven_client = Client(dsn=self.config.get("sentry_dsn"), transport=AioHttpTransport)
        else:
            self._raven_client = None

        self.tb_session = aiohttp.ClientSession()

    def __del__(self):
        # Fuck off asyncio
        self.loop.set_exception_handler(lambda *args, **kwargs: None)

    async def on_socket_response(self, raw_data: json):
        """
        Recieves raw JSON data.

        This is only used to dispatch to hooks.
        """
        for hook in self.hooks.get("on_recv", {}).values():
            self.loop.create_task(hook(raw_data))

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

        # Run error hooks.
        for hook in self.hooks.get("on_error", []):
            self.loop.create_task(hook(event_method, *args, **kwargs))

    async def load_plugins(self):
        """
        Loads plugins from plugins/.
        """
        if not os.path.exists(os.path.join(os.getcwd(), "plugins/")):
            logger.critical("No plugins directory exists. Your bot is effectively useless.")
            return
        # Add cwd to sys.path
        sys.path.insert(0, os.path.join(os.getcwd()))
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
            # Check in the config.
            if name in self.config.get("disabled", []):
                logger.info("Skipping disabled plugin {}.".format(name))
                continue
            import_name = "plugins." + name
            # Import using importlib.
            try:
                mod = importlib.import_module(import_name)
                if hasattr(mod, "load_plugin"):
                    await mod.load_plugin(self)
                self.modules[mod.__name__] = mod
                logger.info("Loaded plugin {} (from {})".format(mod.__name__, mod.__file__))
            except Exception as e:
                logger.error("Error upon loading plugin `{}`! Cannot continue loading.".format(import_name))
                traceback.print_exc()
                continue
        # Remove from path.
        sys.path.pop(0)

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
        await self.load_plugins()

        # Run on_ready hooks
        for hook in self.hooks.get("on_ready", {}).values():
            try:
                await hook(self)
            except:
                logger.error("Caught exception in hook on_ready -> {}".format(hook.__name__))
                traceback.print_exc()
                continue

        # Set the game.
        await self.change_status(discord.Game(name=self.config.get("game_text", "Type ?info for help!")))

    async def on_message(self, message: discord.Message):
        # Increment the message count.
        util.msgcount += 1

        if self.config.get("self_bot"):
            if message.author != message.server.me:
                logger.info("Ignoring message from not me.")
                return

        if message.author.bot:
            logger.info("Ignoring message from bot account.")
            return

        # Load locale.
        _loc_key = await db.get_config(message.server.id, "lang", default=None)
        loc = get_locale(_loc_key)

        # Run on_message_before_blacklist
        for hook in self.hooks.get("on_message_before_blacklist", {}).values():
            ctx = OnMessageEventContext(self, message, loc)
            try:
                result = await hook(ctx)
            except:
                logger.error("Caught exception in hook on_message_before_blacklist -> {}".format(hook.__name__))
                traceback.print_exc()
                continue
            # Don't process if the hook returns True.
            if result:
                logger.info("Hook `on_message_before_blacklist -> {}` forced end of processing.".format(hook.__name__))
                return

        global_blacklist = await db.get_set("global_blacklist") or set()

        # Check if they are globally blacklist.
        if message.author.id in global_blacklist:
            logger.info("Ignoring message from globally blacklisted user.")
            return

        if not isinstance(message.channel, discord.PrivateChannel):
            # print(Fore.RED + message.server.name, ":", Fore.GREEN + message.channel.name, ":",
            #      Fore.CYAN + message.author.name , ":", Fore.RESET + message.content)
            logger.info("Recieved message: {message.content} from {message.author.display_name}"
                        .format(message=message))
            logger.info(" On channel: #{message.channel.name}".format(message=message))

        # Check for a valid server.
        if message.server is not None:
            logger.info(" On server: {} ({})".format(message.server.name, message.server.id))
        else:
            # No DMs
            await self.send_message(message.channel, "I don't accept private messages.")
            return

        # Load set members for blacklist.
        pool = await get_pool()
        async with pool.get() as conn:
            assert isinstance(conn, aioredis.Redis)
            blacklist = await db.get_set("blacklist:{}".format(message.server.id))

        if blacklist and message.author.id in blacklist:
            # Ignore the message.
            logger.info("Ignoring message from blacklisted member {message.author.display_name}"
                        .format(message=message))
            return

        if len(message.content) == 0:
            logger.info("Ignoring (presumably) image-only message.")
            return

        # Run on_message hooks.
        for hook in copy.copy(self.hooks.get("on_message", {})).values():
            ctx = OnMessageEventContext(self, message, loc)
            try:
                await hook(ctx)
            except Exception:
                logger.error("Caught exception in hook on_message -> {}".format(hook.__name__))
                traceback.print_exc()
                continue

    def navalbot(self):
        # Switch login method based on args.
        login = (self.config.get("client", {}).get("oauth_bot_token", ""),)
        try:
            if self.config.get("self_bot", False):
                self.loop.run_until_complete(self.login(*login, bot=False))
            else:
                self.loop.run_until_complete(self.login(*login))
        except discord.errors.HTTPException as e:
            if e.response.status == 401:
                logger.error("Your bot token is incorrect. Cannot login.")
                return
            else:
                raise

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
            logger.error("Crashed.")
            return
