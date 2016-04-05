import discord
import cmds
from exceptions import CommandError

import util


@cmds.command("mute")
@util.with_permission("Admin", "Bot Commander")
async def mute(client: discord.Client, message: discord.Message):
    muterole = discord.utils.get(message.server.roles, name='Muted')

    if not muterole:
        raise CommandError('No Muted role created')

    if len(message.mentions) > 0:
        try:
            await client.add_roles(message.mentions[0], muterole)
            await client.server_voice_state(message.mentions[0], mute=True)
            await client.send_message(message.channel,
                                      'User {} got muted by {}'.format(message.mentions[0], message.author))
        except discord.Forbidden:
            await client.send_message('Not enough permissions to mute user {}'.format(message.mentions[0].name))
            raise CommandError('Not enough permissions to mute user : {}'.format(message.mentions[0].name))
    else:
        await client.send_message(message.channel, "Usage: ?mute @UserName")


@cmds.command("unmute")
@util.with_permission("Admin", "Bot Commander")
async def unmute(client: discord.Client, message: discord.Message):
    muterole = discord.utils.get(message.server.roles, name='Muted')

    if not muterole:
        raise CommandError('No Muted role created')
    if len(message.mentions) > 0:
        try:
            await client.remove_roles(message.mentions[0], muterole)
            await client.server_voice_state(message.mentions[0], mute=False)
            await client.send_message(message.channel,
                                      'User {} got unmuted by {}'.format(message.mentions[0], message.author))
        except discord.Forbidden:
            await client.send_message('Not enough permissions to unmute user {}'.format(message.mentions[0].name))
            raise CommandError('Not enough permissions to unmute user : {}'.format(message.mentions[0].name))
    else:
        await client.send_message(message.channel, "Usage: ?unmute @UserName")


@cmds.command("ban")
@util.with_permission("Admin", "Bot Commander")
async def ban(client: discord.Client, message: discord.Message):
    try:
        await client.ban(member=message.mentions[0]) \
            if len(message.mentions) > 0 \
            else client.send_message(message.channel, content=":question: You must provide a user to ban.")
        await client.send_message(message.channel,
                                  '{} got banned by {}!'.format(message.mentions[0], message.author.name))
    except (discord.Forbidden, IndexError) as banerror:
        print('[ERROR]:', banerror)


@cmds.command("unban")
@util.with_permission("Admin", "Bot Commander")
async def unban(client: discord.Client, message: discord.Message):
    await client.send_message(message.channel, 'Lol, unbans')


@cmds.command("kick")
@util.with_permission("Admin", "Bot Commander")
async def kick(client: discord.Client, message: discord.Message):
    try:
        await client.kick(member=message.mentions[0])
        await client.send_message(message.channel,
                                  '{} got kicked by {}!'.format(message.mentions[0], message.author.name))
    except (discord.Forbidden, IndexError) as kickerror:
        print('[Error]', kickerror)


@cmds.command("delete")
@util.with_permission("Admin", "Bot Commander")
async def delete(client: discord.Client, message: discord.Message, count=None):
    try:
        count = int(' '.join(message.content.split(" ")[1:]))
    except ValueError:
        await client.send_message(message.channel, "This is not a number")
    async for msg in client.logs_from(message.channel, count + 1):
        await client.delete_message(msg)
    if count == 1:
        await client.send_message(message.channel, '**{} message deleted by {}**💣'.format(count, message.author))
    else:
        await client.send_message(message.channel, '**{} messages deleted by {}** 💣'.format(count, message.author))


@cmds.command("inv")
async def inv(client: discord.Client, message: discord.Message):
    try:
        invite = message.content.split(" ")[1]
    except IndexError:
        await client.send_message(message.channel, "No")
        return

    await client.accept_invite(invite)
    await client.send_message(message.channel, "Joined server specified.")
