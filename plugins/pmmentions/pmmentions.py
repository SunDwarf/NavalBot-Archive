"""
PMs you if you get mentioned.
"""
import discord

from navalbot.api import db
from navalbot.api.commands import command, CommandContext
from navalbot.api.hooks import on_message


@on_message
async def check_pm_mention(client: discord.Client, message: discord.Message):
    """
    PMs a user if they have PM mentions enabled.
    """
    mentions = message.mentions
    if len(mentions) < 1:
        # No mentions, no need for PMs.
        return
    to_msg = set(message.mentions)
    # Use a set because it's slightly more performant for multiple mentions.
    # That way, we don't have to call redis every mention.
    for mentioner in to_msg:
        # Get from redis.
        key = await db.get_config(message.server.id, "{}:pmmentions".format(mentioner.id))
        if key and key != "off":
            if key == "away":
                assert isinstance(mentioner, discord.Member)
                if mentioner.status == discord.Status.online:
                    return
            # PM mentions are on, message them.
            constructed = "You have been mentioned:\n\n"
            # Load the last 5 messages.
            msgs = []
            async for mss in client.logs_from(message.channel, limit=5):
                msgs.append(mss)

            msgs = reversed(msgs)

            for mss in msgs:
                # Construct the string
                ts = mss.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC%z")
                constructed += "`[{ts}] {ms.author.display_name}: {ms.clean_content}`\n".format(ts=ts, ms=mss)

            await client.send_message(mentioner, constructed)


@command("pmmentions", argcount=1)
async def pmmentions(ctx: CommandContext):
    """
    Enable or disable PM mentions.
    """
    if ctx.args[0] == "on":
        await ctx.set_config("{}:pmmentions".format(ctx.author.id), "on")
        await ctx.reply("pmmentions.status", status="on")
        return

    if ctx.args[0] == "off":
        await ctx.set_config("{}:pmmentions".format(ctx.author.id), "off")
        await ctx.reply("pmmentions.status", status="off")
        return

    if ctx.args[0] == "away":
        await ctx.set_config("{}:pmmentions".format(ctx.author.id), "away")
        await ctx.reply("pmmentions.status", status="away")
        return

    await ctx.reply("pmmentions.unknown")
