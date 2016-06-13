"""
Hooks for NavalBot.

These make up the **default** hooks, i.e the ones that deal with processing automatically.
These were previously stored in the bot class, but they are now separate.

This means default message processing can be disabled easily, and delegated to a different handler.
"""
import logging
import traceback

import discord
from navalbot import builtins

from navalbot.api import db
from navalbot.api.botcls import NavalClient
from navalbot.api.commands import commands, Command
from navalbot.api.hooks import on_event

logger = logging.getLogger("NavalBot")


@on_event("on_message")
async def command_processor(client: NavalClient, message: discord.Message):
    """
    This is the default command processor for the bot.

    This handles messages and forwards them to commands as appropriate.
    """
    prefix = await db.get_config(message.server.id, "command_prefix", "?")

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
                await coro.invoke(client, message)
                # Delete automatically, only if invocation was successful.
                autodelete = True if await db.get_config(message.server.id, "autodelete") == "True" else False
                if autodelete and message.content.startswith(prefix):
                    await client.delete_message(message)
            else:
                await coro(client, message)
        except Exception as e:
            tb = traceback.format_exc()
            # The limit is 2000.
            # But use 1500 anyway.
            if len(tb) > 1500:
                async with client.tb_session.post("http://dpaste.com/api/v2/", data={"content": tb}) as p:
                    await client.send_message(message.channel,
                                              ":exclamation: Error encountered: {}".format(await p.text()))
            else:
                await client.send_message(message.channel, content="```\n{}\n```".format(traceback.format_exc()))
            # Allow it to fall through.
            raise
