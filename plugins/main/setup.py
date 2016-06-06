"""
This allows setting up of the bot.
"""
import logging

import discord

from navalbot.api import util
from navalbot.api.commands import command, CommandContext
from navalbot.voice.voice_util import find_voice_channel

logger = logging.getLogger("NavalBot")


def _gen_message(perm: bool, name: str) -> str:
    if perm:
        emoji = ":white_check_mark:"
    else:
        emoji = ":white_large_square:"

    return "{} {}\n".format(emoji, name)


async def setup_roles(ctx: CommandContext):
    """
    Setup the roles.
    """
    while True:
        await ctx.send("Please type the name of your Admin role, or None to use 'Admin'.")
        next_msg = await ctx.client.wait_for_message(timeout=10, author=ctx.author, channel=ctx.channel)
        if not next_msg:
            await ctx.send("Cancelling this stage of setup.")
            return
        if next_msg.content.lower().lstrip().rstrip() == "none":
            admin_name = "Admin"
        else:
            admin_name = next_msg.content

        await ctx.send("Please type the name of your Bot Commander role, or None to use 'Bot Commander'.")
        next_msg = await ctx.client.wait_for_message(timeout=10, author=ctx.author, channel=ctx.channel)
        if not next_msg:
            await ctx.send("Cancelling this stage of setup.")
            return
        if next_msg.content.lower().lstrip().rstrip() == "none":
            bot_commander_name = "Bot Commander"
        else:
            bot_commander_name = next_msg.content

        await ctx.send("Please type the name of your Voice role, or None to use 'Voice'.")
        next_msg = await ctx.client.wait_for_message(timeout=10, author=ctx.author, channel=ctx.channel)
        if not next_msg:
            await ctx.send("Cancelling this stage of setup.")
            return
        if next_msg.content.lower().lstrip().rstrip() == "none":
            voice_name = "Voice"
        else:
            voice_name = next_msg.content

        await ctx.send(
            "Applying => `Setup roles '{}', '{}', '{}'`".format(admin_name, bot_commander_name, voice_name)
        )
        await ctx.send("Is this correct? [y/N]")
        next_msg = await ctx.client.wait_for_message(timeout=10, author=ctx.author, channel=ctx.channel)
        if not next_msg or next_msg.content.lower() != "y":
            continue
        else:
            break

    # Create the roles if they do not exist.
    admrole = discord.utils.get(ctx.server.roles, name=admin_name)
    if not admrole:
        admrole = await ctx.client.create_role(ctx.server, name=admin_name)
        await ctx.set_config("role:admin", admin_name)
        await ctx.send(":heavy_check_mark: Config updated: `role:admin` -> `{}`".format(admin_name))

    bcrole = discord.utils.get(ctx.server.roles, name=bot_commander_name)
    if not bcrole:
        bcrole = await ctx.client.create_role(ctx.server, name=bot_commander_name)
        await ctx.set_config("role:bot_commander", bot_commander_name)
        await ctx.send(":heavy_check_mark: Config updated: `role:bot_commander` -> `{}`".format(bot_commander_name))

    vrole = discord.utils.get(ctx.server.roles, name=voice_name)
    if not vrole:
        vrole = await ctx.client.create_role(ctx.server, name=voice_name)
        await ctx.set_config("role:voice", voice_name)
        await ctx.send(":heavy_check_mark: Config updated: `role:voice` -> `{}`".format(voice_name))


async def setup_music(ctx: CommandContext):
    """
    Sets up the music channel.
    """
    while True:
        await ctx.send("Please type the name of the music channel to use, or None for the default (`Music`):")
        next_msg = await ctx.client.wait_for_message(timeout=10, author=ctx.author, channel=ctx.channel)
        if not next_msg:
            await ctx.send("Cancelling this stage of setup.")
            return
        if next_msg.content.lower().lstrip().rstrip() == "none":
            chan = "Music"
        else:
            chan = next_msg.content

        await ctx.send("Is this correct? [y/N]")
        next_msg = await ctx.client.wait_for_message(timeout=10, author=ctx.author, channel=ctx.channel)
        if not next_msg:
            await ctx.send("Cancelling this stage of setup.")
            return
        if next_msg.content.lower() != "y":
            continue
        else:
            break

    # Check if the channel exists.
    assert isinstance(ctx.server, discord.Server)
    for chn in ctx.server.channels:
        assert isinstance(chn, discord.Channel)
        if chn.type != discord.ChannelType.voice:
            continue
        if chn.name.lower() == chan:
            vc = chn
            break
    else:
        vc = None

    if not vc:
        # Create it.
        vc = await ctx.client.create_channel(ctx.server, chan, type=discord.ChannelType.voice)
        await ctx.send(":heavy_check_mark: Server updated: Channel created -> `{}`".format(chan))
    await ctx.set_config("voice_channel", chan)
    await ctx.send(":heavy_check_mark: Config updated: `voice_channel` -> `{}`".format(chan))

    # Set up permissions.
    allow_all = discord.Permissions.none()
    deny_all = discord.Permissions.none()
    deny_all.speak = True

    # Edit the permissions for the voice_channel.
    await ctx.client.edit_channel_permissions(vc, ctx.server.default_role, allow=allow_all, deny=deny_all)
    await ctx.send(":heavy_check_mark: Roles updated: `everyone` -> Deny speaking on {}.".format(chan))

    # Edit our permission.
    allow_me = discord.Permissions.voice()
    await ctx.client.edit_channel_permissions(vc, ctx.me, allow=allow_me)
    await ctx.send(":heavy_check_mark: Roles updated: `{}` -> Allow voice on {}.".format(ctx.me.display_name, chan))


@command("setup")
async def setup(ctx: CommandContext):
    """
    Set up the bot.
    """
    # Check for the right permission.
    perms = ctx.author.permissions_in(ctx.channel)
    if not (perms.administrator or perms.manage_server):
        return

    if await ctx.db.get_key("setup:{}".format(ctx.server.id)):
        await ctx.send("This server is already set up.")
        return

    logger.info("Setting up server {}.".format(ctx.server.name))

    await ctx.send("Setting up NavalBot, loading permissions.")
    # Check my permissions.
    ps = "Permissions: \n"
    perms = ctx.me.permissions_in(ctx.channel)
    assert isinstance(perms, discord.Permissions)
    manage_server = util.has_perm(perms, "manage_server")
    manage_roles = util.has_perm(perms, "manage_roles")
    moderate = all((util.has_perm(perms, "ban_members"), util.has_perm(perms, "kick_members"),
                    util.has_perm(perms, "manage_messages")))

    manage_channels = util.has_perm(perms, "manage_channels")

    # Could be done better.
    ps += _gen_message(manage_server, "Manage server")
    ps += _gen_message(manage_roles, "Manage roles")
    ps += _gen_message(moderate, "Moderation roles")
    ps += _gen_message(manage_channels, "Manage channels")

    await ctx.send(ps)

    if not all((manage_server, manage_roles, manage_channels, moderate)):
        await ctx.send(":warning: I do not have all permissions. Continue setup? [y/N]")
        next_msg = await ctx.client.wait_for_message(timeout=10, author=ctx.author, channel=ctx.channel)
        if not next_msg or next_msg.content.lower() != "y":
            await ctx.send("Cancelling setup.")
            return

    # First step, is create roles.
    if manage_roles:
        await ctx.send("Create initial roles? [y/N]")
        next_msg = await ctx.client.wait_for_message(timeout=10, author=ctx.author, channel=ctx.channel)
        if not next_msg:
            await ctx.send("Timed out, cancelling setup.")
            return
        if next_msg.content.lower() != "y":
            await ctx.send("Skipping role creation.")
        else:
            await setup_roles(ctx)
    else:
        await ctx.send(":warning: Not enough permissions to create roles. Skipping step.")

    if manage_channels:
        await ctx.send("Set up music channel? [y/N]")
        next_msg = await ctx.client.wait_for_message(timeout=10, author=ctx.author, channel=ctx.channel)
        if not next_msg:
            await ctx.send("Timed out, cancelling setup.")
            return
        if next_msg.content.lower() != "y":
            await ctx.send("Skipping music channel creation.")
        else:
            await setup_music(ctx)

    await ctx.send("Do you want to set a channel language? [y/N]")
    next_msg = await ctx.client.wait_for_message(timeout=10, author=ctx.author, channel=ctx.channel)
    if not next_msg:
        await ctx.send("Timed out, cancelling setup.")
        return
    if next_msg.content.lower() != "y":
        await ctx.send("Setting language to en.")
    else:
        await ctx.send("Type the two-letter language code you wish to set. This language may not have translations "
                       "yet, however.")
        next_msg = await ctx.client.wait_for_message(timeout=10, author=ctx.author, channel=ctx.channel)
        if not next_msg:
            lang = None
        else:
            lang = next_msg.content.lower()

        if lang:
            await ctx.set_config("lang", lang)
            await ctx.send(":heavy_check_mark: Config updated: `lang` -> `{}`".format(lang))
        else:
            await ctx.send("Using English for language.")

    await ctx.send("Setup complete.")
    await ctx.db.set_key("setup:{}".format(ctx.server.id), "y")
