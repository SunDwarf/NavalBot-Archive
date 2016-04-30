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

import asyncio
from concurrent.futures.process import BrokenProcessPool
import datetime
import functools
import os
import random

import db
import discord
import psutil
import pyowm
import urbandict
import praw
from google import search
from googleapiclient.discovery import build

import cmds
import util

loop = asyncio.get_event_loop()

r = praw.Reddit(user_agent='NavalBot/3.x for Discord')


@cmds.command("choice")
@util.enforce_args(2)
async def choice(client: discord.Client, message: discord.Message, args: list):
    """
    Makes that hard choice for you.
    """
    # Choose a random argument from the list.
    chosen = random.choice(args)
    await client.send_message(message.channel, "My choice was: `{}`".format(chosen))


def _get_google(f):
    return list(f())[0]


@cmds.command("google")
async def google(client: discord.Client, message: discord.Message):
    """
    Searches google for the top two results for the search.
    """
    userinput = ' '.join(message.content.split(" ")[1:])
    f = functools.partial(search, userinput, stop=1)
    f2 = functools.partial(_get_google, f)
    l = await util.with_multiprocessing(f2)
    await client.send_message(message.channel, l)


def _get_weather(api_key, userinput):
    owm = pyowm.OWM(api_key)
    observation = owm.weather_at_place(userinput)
    # Get the weather and stuff.
    w = observation.get_weather()
    wind = w.get_wind()['speed']
    humidity = w.get_humidity()
    temp = w.get_temperature('celsius')['temp']
    return wind, humidity, temp


@cmds.command("weather")
@util.enforce_args(1, ":x: You must specify a village/town/city/settlement to query!")
async def weather(client: discord.Client, message: discord.Message, args: list):
    """
    Displays the weather of a specified place.
    """
    api_key = await db.get_key("owm_key")
    if not api_key:
        await client.send_message(message.channel, ":exclamation: You have not set the API key. Set it with `setcfg "
                                                   "owm_api_key <your_api_key>`.")
        return
    try:
        userinput = ' '.join(args[0:])
        try:
            wind, humidity, temp = await util.with_multiprocessing(functools.partial(_get_weather, api_key, userinput))
        except BrokenProcessPool:
            await client.send_message(message.channel, ":exclamation: Hit the rate limit. Please wait.")
            return
        await client.send_message(
            message.channel,
            '☁_Weather for {}:_\n** Temperature:** {} °C **Humidity:** {} % **Wind:** {} m/s'
                .format(userinput, temp, humidity, wind)
        )
    except AttributeError:
        await client.send_message(message.channel, "This city does not exist")


@cmds.command("info")
@cmds.command("commands")
async def commands(client: discord.Client, message: discord.Message):
    """
    Gives a link for information about the bot.
    """
    await client.send_message(message.channel, "**See https://github.com/SunDwarf/NavalBot/wiki for more info.**")


@cmds.command("whois")
async def whois(client: discord.Client, message: discord.Message):
    """
    Displays information about the user specified.
    """
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
    """
    Gives the uptime of the bot.
    """
    upt = datetime.datetime.now() - util.startup
    s = upt.total_seconds()
    formatted = util.format_timedelta(s, "`{hours_total} hours, {minutes} minutes, {seconds} seconds`")
    await client.send_message(message.channel, "Bot has been running for {} since startup of process `#{}`"
                              .format(formatted, os.getpid()))


@cmds.command("stats")
async def stats(client: discord.Client, message: discord.Message):
    """
    Displays statistics about the currently running bot.
    """
    server_count = len(client.servers)
    msgcount = util.msgcount
    if isinstance(client.voice, dict):
        voice_clients = len(client.voice)
    else:
        voice_clients = 1 if client.is_voice_connected() else 0
    streams = sum([1 for proc in psutil.process_iter() if proc.name() == "ffmpeg"])
    # Memory stats
    used_memory = psutil.Process().memory_info().rss
    used_memory = round(used_memory / 1024 / 1024, 2)
    if client.shard_id is not None:
        shardm = "Currently shard `{}/{}`.\n".format(client.shard_id + 1, client.shard_count)
    else:
        shardm = ""
    await client.send_message(
        message.channel,
        shardm +
        "Currently running on `{}` server(s). Processed `{}` messages since startup.\n"
        "Connected to `{}` voice channels, with `{}` streams currently playing.\n"
        "Using `{}MB` of memory."
            .format(server_count, msgcount, voice_clients, streams, used_memory))


@cmds.command("searchyt")
@util.enforce_args(1, ":x: You must enter something to search for!")
async def search_youtube(client: discord.Client, message: discord.Message, args: list):
    """
    Searches YouTube for the specified tags.
    """
    # Join up the args
    to_search = " ".join(args)
    # Get the API key
    api_key = await db.get_key("youtube_api_key")
    if not api_key:
        await client.send_message(message.channel,
                                  ':x: The YouTube Data API v3 key has not been set!\n'
                                  ':x:Set it with `?setconfig "youtube_api_key" "key"`.')
        return

    # Create a new instance of the APIClient
    yt_api_client = build("youtube", "v3", developerKey=api_key)
    built = yt_api_client.search().list(
        q=to_search,
        part="id,snippet",
        maxResults=1
    )
    search_response = await loop.run_in_executor(None, built.execute)

    items = search_response.get("items", [])
    if not items:
        await client.send_message(message.channel, ":no_entry: No results found for your search.")
        return

    # Load the video data
    video_data = items[0]
    if video_data["id"]["kind"] != "youtube#video":
        await client.send_message(message.channel, ":no_entry: No relevant videos found for your search.")
        return

    title = video_data["snippet"]["title"]
    link = "https://youtube.com/watch?v=" + video_data["id"]["videoId"]
    await client.send_message(message.channel, "**{}**\n{}".format(title, link))


@cmds.command("coin")
async def coin(client: discord.Client, message: discord.Message):
    """
    Flip a coin!
    """
    random_choice = (["Heads!"] * 49) + (["Tails!"] * 49) + ["On the side!"]
    await client.send_message(message.channel, random.choice(random_choice))


@cmds.command("remindme")
@util.enforce_args(2, error_msg=":x: You must provide a time and reason!")
async def remind_me(client: discord.Client, message: discord.Message, args: list):
    """
    Set a reminder.
    """
    time = args[0]
    try:
        time = int(time)
    except ValueError:
        await client.send_message(message.channel, ":x: That is not a valid time in seconds!")
        return
    to_remind = ' '.join(args[1:])

    async def __remind_coro():
        await asyncio.sleep(time)
        await client.send_message(message.channel,
                                  "{message.author.mention} Reminder for: `{r}`".format(message=message, r=to_remind))
        return

    await client.send_message(
        message.channel,
        "{message.author.mention} Ok, reminding you in `{s}` seconds for `{r}`.".format(message=message, r=to_remind,
                                                                                        s=time)
    )

    loop.create_task(__remind_coro())


@cmds.command("source")
@util.enforce_args(1, error_msg=":x: Must provide a function to lookup source for.")
async def get_source(client: discord.Client, message: discord.Message, args: list):
    """
    Displays the source code of a specific command.
    """
    base_url = "https://github.com/SunDwarf/NavalBot/"

    if not args[0] in cmds.commands:
        await client.send_message(message.channel, ":x: This function does exist")
        return

    func = cmds.commands[args[0]]
    # check for decorated cmds
    if hasattr(func, 'func'):
        func = func.func

    co = func.__code__
    location = os.path.relpath(co.co_filename).replace('\\', '/')

    final_url = '<{}/blob/develop/{}#L{}>'.format(base_url, location, co.co_firstlineno)
    await client.send_message(message.channel, final_url)


@cmds.command("echo")
@util.owner
@util.enforce_args(3, error_msg=":x: Must give server ID, channel name, message")
async def echo(client: discord.Client, message: discord.Message, args: list):
    """
    Sends a message to a specific server.
    You have to provide the server ID, channel name and message.
    """
    server = client.get_server(args[0])
    if not server:
        await client.send_message(message.channel, ":x: No such server found")
        return

    channel = discord.utils.get(server.channels, name=args[1])
    if not channel:
        await client.send_message(message.channel, ":x: No such channel found")
        return

    await client.send_message(channel, args[2])


@cmds.command("factoid")
async def factoid(client: discord.Client, message: discord.Message):
    """
    Displays help on how to create a factoid.
    """
    prefix = await db.get_config(message.server.id, "command_prefix", "?")
    await client.send_message(message.channel,
                              "You can create a factoid by typing `{}<factoid_name> is <answer>`".format(prefix))


def _get_urban(get):
    define = urbandict.define(get)[0]
    return define['word'], define['def'], define['example']


@cmds.command("urban")
@util.enforce_args(1, error_msg="You have to provide a word!")
async def urban(client: discord.Client, message: discord.Message, args: list):
    """
    Defines a word using urban dictionary.
    """
    word, definition, example = await util.with_multiprocessing(functools.partial(_get_urban, ' '.join(args)))
    await client.send_message(message.channel,
                              "*Your search for `{}` returned the following:*\n\n**Definition:** {}\n\n**Example:** {}"
                              .format(word, definition, example))


def _get_sr_data(arg):
    subreddit = r.get_subreddit(arg)
    if not subreddit or subreddit.over18:
        return
    submissions = list(subreddit.get_hot(limit=30))
    # shuffle
    random.shuffle(submissions)
    sub = submissions[0]
    return sub.url


@cmds.command("sr")
@util.enforce_args(1, error_msg=":x: You must provide a subreddit.")
async def subreddit(client: discord.Client, message: discord.Message, args: list):
    """
    Fetches random post from subreddit's front page.
    """
    sr_link = await util.with_multiprocessing(functools.partial(_get_sr_data, args[0]))
    if not sr_link:
        await client.send_message(message.channel, ":x: Subreddit either doesn't exist or is NSFW.")
        return
    await client.send_message(message.channel, sr_link)