import datetime
import os
import random

import discord
import pyowm
from google import search

import cmds
import nsfw
import red
import util


@cmds.command("choice")
@util.enforce_args(2)
async def choice(client: discord.Client, message: discord.Message, args: list):
    # Choose a random argument from the list.
    chosen = random.choice(args)
    await client.send_message(message.channel, "My choice was: `{}`".format(chosen))

@cmds.command("info")
async def info(client: discord.Client, message: discord.Message):
    await client.send_message(message.channel, "{} `Ok, check your private messages` 👍".format(message.author.mention))
    await client.send_message(message.author, 'TODO: ADD SOMETHING HERE')


@cmds.command("google")
async def google(client: discord.Client, message: discord.Message):
    userinput = ' '.join(message.content.split(" ")[1:])
    await client.send_message(message.channel, "The links have been sent to you {}".format(message.author))
    for url in search(userinput, stop=2):
        await client.send_message(message.author, url)


@cmds.command("weather")
async def weather(client: discord.Client, message: discord.Message):
    api_key = util.get_config("owm_api_key")
    if not api_key:
        await client.send_message(message.channel, ":exclamation: You have not set the API key. Set it with `setcfg "
                                                   "owm_api_key <your_api_key>`.")
        return
    owm = pyowm.OWM(api_key)
    try:
        userinput = ' '.join(message.content.split(" ")[1:])
        # Get it from the place
        observation = owm.weather_at_place(userinput)
        # Get the weather and stuff.
        w = observation.get_weather()
        wind = w.get_wind()['speed']
        humidity = w.get_humidity()
        temp = w.get_temperature('celsius')['temp']
        await client.send_message(
            message.channel,
            '☁__Weather for {}:__\n** Temperature:** {} °C **Humidity:** {} % **Wind:** {} m/s'
                .format(userinput, temp, humidity, wind)
        )
    except AttributeError:
        await client.send_message(message.channel, "This city does not exist")


@cmds.command("commands")
async def commands(client: discord.Client, message: discord.Message):
    com = ['-lock', '-guess', '-reddit', '-info', '-servers', '-version', '-weather', '-whois', '-uptime', '-google',
           '-invite''\n**Admins only:**', '-game', '-kick', '-ban', '-unban', '-mute', '-unmute', '-delete', '-getcfg',
           '-setcfg', '-py', '-sql']
    await client.send_message(message.channel, "**These commands are available:**\n{}".format('\n'.join(com)))


@cmds.command("reddit")
async def reddit(client: discord.Client, message: discord.Message):
    try:
        choice = ' '.join(message.content.split(" ")[1:]).lower()
        if choice in nsfw.PURITAN_VALUES:
            await client.send_message(message.channel, 'You´re not supposed to search for this ಠ_ಠ')
        else:
            await client.send_message(message.channel, 'The top posts from {} have been sent to you'.format(choice))
            red_fetched = red.main(userchoice=choice)
            for link in red_fetched:
                await client.send_message(message.author, content=link)
    except TypeError as f:
        print('[ERROR]', f)


@cmds.command("whois")
async def whois(client: discord.Client, message: discord.Message):
    try:
        await client.send_message(message.channel,
                                  '**Name:** {}\n**ID:** `{}`\n**Created at:** {}\n**Avatar:** {}'.format(
                                      message.mentions[0],
                                      message.mentions[0].id,
                                      message.mentions[0].created_at,
                                      message.mentions[0].avatar_url,
                                  ))
    except IndexError:
        await client.send_message(message.channel, "Usage: ?whois @UserName")


@cmds.command("uptime")
async def uptime(client: discord.Client, message: discord.Message):
    upt = datetime.datetime.now() - util.startup
    s = upt.total_seconds()
    formatted = util.format_timedelta(s, "`{hours_total} hours, {minutes} minutes, {seconds} seconds`")
    await client.send_message(message.channel, "Bot has been running for {} since startup of process `#{}`"
                              .format(formatted, os.getpid()))
