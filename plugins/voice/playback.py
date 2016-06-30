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
import re
from concurrent.futures import TimeoutError

import discord
import youtube_dl

from navalbot.api import db
from navalbot.api import util
from navalbot.api.commands import command
from navalbot.api.commands.cmdclass import NavalRole
from navalbot.api.contexts import CommandContext
from .stores import voice_locks

# Get loop
from navalbot.voice.voice_util import find_voice_channel, author_is_valid

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
async def reset(ctx: CommandContext):
    # Unlock the lock, if it's locked.
    lock = voice_locks.get(ctx.message.server.id)
    if lock:
        del voice_locks[ctx.message.server.id]

    vc = ctx.client.voice_client_in(ctx.message.server)
    if not vc:
        # Send a voice state to kill the connection, even if it doesn't exist.
        await ctx.client.ws.voice_state(ctx.server.id, None, self_mute=True)
        await ctx.reply("voice.reset.success")
        return

    # Reset the voice client
    channels = [vc.channel, find_voice_channel(ctx.message.server), ctx.message.author.voice_channel]

    if not author_is_valid(ctx.message.author, channels):
        await ctx.reply("voice.cant_control")
        return

    await vc.reset()
    await ctx.reply("voice.reset.success")


@command("release", role={NavalRole.ADMIN, NavalRole.BOT_COMMANDER, NavalRole.VOICE})
async def release(ctx: CommandContext):
    """
    Attempt to release the voice lock.
    """
    lock = voice_locks.get(ctx.message.server.id)
    if not lock:
        return

    assert isinstance(lock, asyncio.Lock)
    while True:
        try:
            lock.release()
        except RuntimeError:
            return


@command("np", "nowplaying")
async def np(ctx: CommandContext):
    """
    Get the currently playing track.
    """
    vc = ctx.client.voice_client_in(ctx.message.server)
    if not vc:
        await ctx.reply("voice.not_connected")
        return

    # Return the output of `cmd_np`.
    await vc.cmd_np(ctx)


def coro_factory(coro, *args, **kwargs):
    """
    This function is called to create a factory, which can be used to create infinitely as many copies of the
    playback coroutine as you need.

    Used for ?again, mostly.
    """
    return functools.partial(coro, *args, **kwargs)


@command("play", "playyt", "playyoutube", argcount="?", argerror=":x: You must pass a video!")
async def play(ctx: CommandContext):
    """
    Plays a video from any valid streaming source that `youtube-dl` can download from.
    This includes things such as YouTube (obviously) and SoundCloud.
    You must have the Voice or Bot Commander role to use this command.
    Use ?stop or ?skip to skip a song, ?queue to see the current queue of songs, ?np to see the currently playing
    track, and ?reset to fix the queue.
    """
    voice_channel = await find_voice_channel(ctx.message.server)
    if not voice_channel:
        # await client.send_message(
        #    message.channel,
        #    content=":x: Cannot find voice channel for playing music! This defaults to `NavalBot` or `Music`, "
        #            "however you can override this with by running `{}setcfg voice_channel <your channel>`."
        #        .format(await util.get_prefix(message.server.id)))
        await ctx.reply("voice.playback.no_channel", prefix=await util.get_prefix(ctx.message.server.id))
        return

    if ctx.message.server.id not in voice_locks:
        voice_locks[ctx.message.server.id] = asyncio.Lock()

    vidname = ' '.join(ctx.args)

    if 'list' in vidname or 'playlist' in vidname:
        await ctx.reply("voice.playback.pl_warning")

    # Naive implementation of preventing naughtystuff
    if re.match(r'.*http[s]://.*', vidname):
        limit = await db.get_config(ctx.message.server.id, "limit_urls", default="True", type_=str)
        limit = True if limit == "True" else False
        if limit:
            # Only allow youtube/soundcloud links
            if not re.match(r'.*?(youtube.com|youtu.be|soundcloud.com).*?', vidname):
                await ctx.reply("voice.playback.bad_url",
                                prefix=await db.get_config(ctx.message.server.id, "command_prefix", default="?"))
                return

    # Do the same as play_file, but with a youtube streamer.
    # Play it via ffmpeg.

    # Get the max queue size
    qsize = await db.get_config(ctx.message.server.id, "max_queue", default=99, type_=int)

    # Use fallback for soundcloud, if possible
    ydl = youtube_dl.YoutubeDL({
        "format": 'best', "ignoreerrors": True, "playlistend": qsize,
        "default_search": "ytsearch", "source_address": "0.0.0.0"})
    func = functools.partial(ydl.extract_info, vidname, download=False)
    # Set the download lock.
    lock = voice_locks.get(ctx.message.server.id)
    assert isinstance(lock, asyncio.Lock)
    try:
        if lock.locked():
            await ctx.reply("voice.playback.wait_for")
        await lock.acquire()
        await ctx.reply("voice.playback.downloading")
        info = await loop.run_in_executor(None, func)
        try:
            lock.release()
        except RuntimeError:
            try:
                del voice_locks[ctx.message.server.id]
            except Exception:
                pass
    except Exception as e:
        await ctx.reply("voice.playback.ytdl_error", err=e)
        try:
            lock.release()
        except RuntimeError:
            try:
                del voice_locks[ctx.message.server.id]
            except Exception:
                pass
        return

    if not info:
        await ctx.reply("voice.playback.bad_info")
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
        download_url = info['url']

        # Change the duration if it is live.
        if info.get("is_live"):
            info["duration"] = 0

        pl_data = None

    # What this coroutine does:
    # 1. Checks for the queue of a specific server.
    #    If it doesn't find one, it creates a new one. It then opens a new voice connection to the server.
    # 2. Places the coroutine on the server-specific queue.
    # 3. Checks to see if there is a looping task running for fetching new songs off of the queue for that server.
    #    If there isn't, it will create a new one, store it, and so on.
    if not ctx.client.is_voice_connected(ctx.message.server):
        try:
            voice_client = await ctx.client.join_voice_channel(channel=voice_channel)
        except (discord.ClientException, TimeoutError, asyncio.TimeoutError):
            await ctx.reply("voice.playback.timeout")
            return
    else:
        voice_client = ctx.client.voice_client_in(ctx.message.server)
        # Check if we're connected anyway.
        # This works around some weird bugs.
        if not voice_client.is_connected():
            # Since we're not, delete the voice client and re-try.
            try:
                del ctx.client.connection._voice_clients[ctx.message.server.id]
            except Exception:
                # lol what
                pass
            # Re-create the voice client.
            try:
                voice_client = await ctx.client.join_voice_channel(channel=voice_channel)
            except (discord.ClientException, TimeoutError, asyncio.TimeoutError):
                await ctx.reply("voice.playback.connection_error")
                return

    queue = voice_client._play_queue

    # Get the number of songs on the queue.
    items = queue.qsize()

    # Switch based on if we're a playlist.
    if not is_playlist:
        # Send a helpful error message.
        if items != 0:
            await ctx.reply("voice.playback.queue_num", pos=items + 1)
        else:
            await ctx.reply("voice.playback.queue_next")

        try:
            # Create the factory.
            fac = coro_factory(voice_client.oauth2_play, ctx, download_url, info)
            queue.put_nowait((fac, info))
        except asyncio.QueueFull:
            await ctx.reply("voice.playback.queue_full")
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
                # I'm not entirely sure this message will ever be seen.
                await ctx.reply("skip_extra")
                break
            # Add it to the queue.
            try:
                # Create the coro factory
                fac = coro_factory(voice_client.oauth2_play, ctx, item["url"], item)
                queue.put_nowait((fac, item))
            except asyncio.QueueFull:
                await ctx.reply("voice.playback.pl_queue_full", limit=num)
                break

        # See above, to see justification of num being -1.
        if num == -1:
            await ctx.reply("voice.playlist.pl_error")
            return

        await ctx.reply("voice.playlist.pl_added", num=num + 1)

    # Create a new task for the VC, as appropriate.
    voice_client.ensure_playlist_task()
