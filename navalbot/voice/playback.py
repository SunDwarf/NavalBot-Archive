"""
=================================

This file is part of NavalBot.
Copyright (C) 2016 Isaac Dickinson

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
import functools
import logging
import re
from math import trunc
from concurrent.futures import TimeoutError

import discord
import youtube_dl

from navalbot.api.commands import oldcommand, command
from navalbot.api import db
from navalbot.api import decorators
from navalbot.api import util
from navalbot.api.commands.cmdclass import NavalRole
from navalbot.voice.voiceclient import NavalVoiceClient
from .stores import voice_params, voice_locks

# Get loop
from .voice_util import find_voice_channel, with_existing_server, with_opus, author_is_valid

loop = asyncio.get_event_loop()


async def _fix_voice(client: discord.Client, vc: discord.VoiceClient, channel: discord.Channel):
    """
    Fixes a voice client.

    If it is invalid, it destroys it and creates a new one.
    """
    if not hasattr(vc, 'ws') or not vc.ws.open or not vc.is_connected():
        # Fix it.
        try:
            await asyncio.wait_for(vc.disconnect(), timeout=1)
        except Exception:
            # Tried to send on a closed web socket. We can safely ignore this
            pass
        new_vc = await client.join_voice_channel(channel)
        return new_vc
    else:
        return vc


@command("reset", "disconnect", roles={NavalRole.ADMIN, NavalRole.BOT_COMMANDER, NavalRole.VOICE})
async def reset(client: discord.Client, message: discord.Message):
    vc = client.voice_client_in(message.server)
    if not vc:
        await client.send_message(message.channel, ":x: Not currently connected in this server.")
        return

    # Reset the voice client
    channels = [vc.channel, find_voice_channel(message.server), message.author.voice_channel]

    if not author_is_valid(message.author, channels):
        await client.send_message(message.channel, ":x: You must be in voice and not deafened to control me.")
        return

    await vc.reset()
    await client.send_message(message.channel, ":heavy_check_mark: Reset voice.")


@command("np", "nowplaying")
async def np(client: discord.Client, message: discord.Message):
    """
    Get the currently playing track.
    """
    vc = client.voice_client_in(message.server)
    if not vc:
        await client.send_message(message.channel, ":x: Not currently connected in this server.")
        return

    # Return the output of `cmd_np`.
    await client.send_message(message.channel, vc.cmd_np())


def coro_factory(coro, *args, **kwargs):
    """
    This function is called to create a factory, which can be used to create infinitely as many copies of the
    playback coroutine as you need.

    Used for ?again, mostly.
    """
    return functools.partial(coro, *args, **kwargs)


@command("play", "playyt", "playyoutube", argcount="?", argerror=":x: You must pass a video!")
async def play(client: discord.Client, message: discord.Message, *args: list):
    """
    Plays a video from any valid streaming source that `youtube-dl` can download from.
    This includes things such as YouTube (obviously) and SoundCloud.
    You must have the Voice or Bot Commander role to use this command.
    Use ?stop or ?skip to skip a song, ?queue to see the current queue of songs, ?np to see the currently playing
    track, and ?reset to fix the queue.
    """
    voice_channel = await find_voice_channel(message.server)
    if not voice_channel:
        await client.send_message(
            message.channel,
            content=":x: Cannot find voice channel for playing music! This defaults to `NavalBot` or `Music`, "
                    "however you can override this with by running `{}setcfg voice_channel <your channel>`."
                .format(await util.get_prefix(message.server.id)))
        return

    if message.server.id not in voice_locks:
        voice_locks[message.server.id] = asyncio.Lock()

    vidname = ' '.join(args)

    if 'list' in vidname or 'playlist' in vidname:
        await client.send_message(message.channel, ":warning: If this is a playlist, it may take a long time to "
                                                   "download.")

    # Naive implementation of preventing naughtystuff
    if re.match(r'http[s]://', vidname):
        limit = await db.get_config(message.server.id, "limit_urls", default="True", type_=str)
        limit = True if limit == "True" else False
        if limit:
            # Only allow youtube/soundcloud links
            if not re.match(r'.*?(youtube.com|youtu.be|soundcloud.com).*?', vidname):
                await client.send_message(
                    message.channel, ":x: This link is not in the link whitelist."
                                     "To turn this off, use `{}setcfg limit_urls False`."
                        .format(await db.get_config(message.server.id, "command_prefix", default="?")))
                return

    # Do the same as play_file, but with a youtube streamer.
    # Play it via ffmpeg.

    # Get the max queue size
    qsize = await db.get_config(message.server.id, "max_queue", default=99, type_=int)

    # Use fallback for soundcloud, if possible
    ydl = youtube_dl.YoutubeDL({
        "format": 'best', "ignoreerrors": True, "playlistend": qsize,
        "default_search": "ytsearch", "source_address": "0.0.0.0"})
    func = functools.partial(ydl.extract_info, vidname, download=False)
    # Set the download lock.
    lock = voice_locks.get(message.server.id)
    assert isinstance(lock, asyncio.Lock)
    try:
        if lock.locked():
            await client.send_message(message.channel, ":hourglass: Something else is downloading. Waiting for that "
                                                       "to finish.")
        await lock.acquire()
        await client.send_message(message.channel, ":hourglass: Downloading video information...")
        info = await loop.run_in_executor(None, func)
        lock.release()
    except Exception as e:
        await client.send_message(message.channel, ":no_entry: Something went horribly wrong. Error: {}".format(e))
        lock.release()
        return

    if not info:
        await client.send_message(message.channel, ":no_entry: Something went horribly wrong. Could not get video "
                                                   "information.")
        return

    # Check for a playlist.
    if "entries" in info and len(info['entries']) > 1:
        # Playlist!
        is_playlist = True
        pl_data = info['entries']
    else:
        # We might be a single video inside a playlist. Get that out.
        if 'entries' in info:
            info = info['entries'][0]
        is_playlist = False
        title = info.get('title')
        download_url = info['url']

        pl_data = None

    # Contrary to the name, this file DOES use queues.
    # However, unlike voice_queue, OAuth2 bots can run on multiple voice servers at once.
    # This means multiple queues can be used per bot.

    # What this coroutine does:
    # 1. Checks for the queue of a specific server.
    #    If it doesn't find one, it creates a new one. It then opens a new voice connection to the server.
    # 2. Places the coroutine on the server-specific queue.
    # 3. Checks to see if there is a looping task running for fetching new songs off of the queue for that server.
    #    If there isn't, it will create a new one, store it, and so on.
    if not client.is_voice_connected(message.server):
        try:
            voice_client = await client.join_voice_channel(channel=voice_channel)
        except (discord.ClientException, TimeoutError, asyncio.TimeoutError):
            await client.send_message(message.channel, ":x: Timed out trying to connect to server.")
            return
    else:
        voice_client = client.voice_client_in(message.server)
        assert isinstance(voice_client, NavalVoiceClient)
        if not voice_client.is_connected():
            try:
                del client.connection._voice_clients[message.server.id]
            except Exception:
                # lol what
                pass
            # Re-create the voice client.
            try:
                voice_client = await client.join_voice_channel(channel=voice_channel)
            except (discord.ClientException, TimeoutError, asyncio.TimeoutError):
                await client.send_message(message.channel, ":x: Error happened on connecting to voice.")
                return

    queue = voice_client._play_queue

    # Get the number of songs on the queue.
    items = queue.qsize()

    # Switch based on if we're a playlist.
    if not is_playlist:
        # Send a helpful error message.
        if items != 0:
            await client.send_message(message.channel,
                                      ":heavy_check_mark: You are number {} in the queue.".format(items + 1))
        else:
            await client.send_message(message.channel, ":heavy_check_mark: You are next in the queue.")

        try:
            # Create the factory.
            fac = coro_factory(voice_client.oauth2_play, client, message, download_url, info)
            queue.put_nowait((fac, info))
        except asyncio.QueueFull:
            await client.send_message(message.channel,
                                      ":no_entry: There are too many songs on the queue. Cannot start "
                                      "playing.")

    else:
        # If it's pretending to be a playlist, but there's nothing there, set num to -1 to prevent UnboundLocalError
        if not pl_data:
            num = -1
        # Loop over each item from the playlist.
        for num, item in enumerate(pl_data):
            if not item:
                continue
            # If the playlist is bigger than the queue, stop it from putting onto the queue.
            if num == qsize:
                await client.send_message(
                    message.channel,
                    ":grey_exclamation: Cannot play more than {} "
                    "songs from a playlist. Skipping the rest.".format(qsize)
                )
                break
            # Add it to the queue.
            try:
                # Create the coro factory

                fac = coro_factory(voice_client.oauth2_play, client, message, item["url"], item)
                queue.put_nowait((fac, item))
            except asyncio.QueueFull:
                await client.send_message(
                    message.channel, ":no_entry: There are too many songs on the queue. "
                                     "Limiting playlist to {}.".format(num)
                )
                break

        # See above, to see justification of num being -1.
        if num == -1:
            await client.send_message(
                message.channel,
                ":x: Search returned nothing, or playlist errored."
            )
            return

        await client.send_message(message.channel, ":heavy_check_mark: Added {} track(s) to queue.".format(num + 1))

    # Create a new task for the VC, as appropriate.
    voice_client.ensure_playlist_task()
