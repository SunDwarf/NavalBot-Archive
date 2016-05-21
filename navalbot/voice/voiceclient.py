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

# Contains the overridded voice client class.
import asyncio
import logging
import random
from math import trunc, ceil

import discord
import functools
import youtube_dl

from navalbot.api import db

logger = logging.getLogger("NavalBot::Voice")


class NavalVoiceClient(discord.VoiceClient):
    """
    Overridden voice client, that allows less of a fustercluck in the voice code.
    """

    def __init__(self, user, main_ws, session_id, channel, data, loop):
        """
        Overridden init.
        """
        super().__init__(user, main_ws, session_id, channel, data, loop)

        self._play_queue = asyncio.Queue()

        # Used for the current status or so.
        self.coro_factory = None
        self.player = None
        self.playing = False
        self.title = "N/A"
        self.progress = 0
        self.duration = 0

        self.curr_task = None

        self.voteskips = []
        self.curr_info = {}

        self.loop.create_task(self._fix_queue())

    async def _fix_queue(self):
        """
        Update the class' queue with the correct queue size.
        """
        qsize = await db.get_config(self.server.id, "max_queue", default=99, type_=int)
        self._play_queue._maxsize = qsize

    async def _await_queue(self):
        # Awaits new songs on the queue.
        while True:
            # Get the queue, fresh.
            # Why?
            # So we can shuffle it.
            logger.info("Running iteration of voice task for server `{}`...".format(self.server))
            queue = self._play_queue
            if not queue:
                return
            try:
                items = await queue.get()
            except RuntimeError as e:
                logger.error(e)
                return
            logger.info("Got new items for `{}`, awaiting.".format(self.server))
            # Place the current coroutine on the voice_params
            self.coro_factory = items[0]
            # Await the playing coroutine.
            await self.coro_factory()

    def ensure_playlist_task(self):
        """
        Ensures the playlist task is running.
        """
        if not self.curr_task or self.curr_task.cancelled():
            self.curr_task = self.loop.create_task(self._await_queue())

    async def _fix_sc(self, download_url: str, wp_url: str) -> str:
        """
        Fix video links, on long playlists.
        """
        if not wp_url:
            logging.getLogger("NavalBot").info("No need to fix up track {}...".format(wp_url))
            return download_url

        logger.info("Fixing up track {}...".format(wp_url))

        ydl = youtube_dl.YoutubeDL(
            {"format": 'webm[abr>0]/bestaudio/best', "ignoreerrors": True, "source_address": "0.0.0.0"})

        # Await to get the new item.
        func = functools.partial(ydl.extract_info, wp_url, download=False)
        data = await self.loop.run_in_executor(None, func)

        logger.info("Fixed up track {}, got new URL: {}".format(wp_url, download_url != data.get("url")))

        return data.get("url")

    async def oauth2_play(self, client: discord.Client,
                          message: discord.Message,
                          download_url: str, info: dict):
        """
        Co-routine that is used for the message queue.
        """
        # Fix the URL.
        download_url = await self._fix_sc(download_url, info.get("webpage_url"))
        # Create a new ffmpeg player.
        player = self.create_ffmpeg_player(download_url)
        # Set the appropriate data.
        self.player = player
        self.playing = True
        self.title = info.get("title", "???")

        self.curr_info = info

        # Reset progress/duration
        self.progress = 0
        self.duration = info.get("duration")
        # Reset voteskips.
        self.voteskips = []
        # Send a now playing message.
        await client.send_message(message.channel,
                                  ":heavy_check_mark: Now playing: `{}`".format(info.get("title", "???")))
        assert isinstance(player, discord.voice_client.ProcessPlayer)

        player.start()
        # Check every 0.5 seconds if we're done or not.
        # 0.5 is non-noticable delay, but doesn't kill the CPU.
        while True:
            if player.is_done():
                break
            else:
                if player.is_playing():
                    # TODO: Use time.time instead
                    self.progress += 0.5
                await asyncio.sleep(0.5)
        # Reset everything now we are done.
        self.playing = False
        self.player = None
        self.duration = 0
        self.progress = 0
        self.voteskips = []
        self.title = None
        self.curr_info = {}

    def cmd_np(self):
        """
        Returns the message for the currently playing track.
        """
        if not self.playing:
            return ":x: No song is currently playing."

        m, s = divmod(self.progress, 60)
        if self.duration:
            dm, ds = divmod(self.duration, 60)
        else:
            dm, ds = 0, 0
        playing = "" if self.player.is_playing() else "`[PAUSED]`"

        # Build the string
        d_str = "[{:02d}:{:02d} / {:02d}:{:02d}]".format(trunc(m), trunc(s), trunc(dm), trunc(ds))
        b_str = "Currently playing: `{}` `{}` {}".format(self.title, d_str, playing)
        return b_str

    async def cmd_queue(self, start_pos: int = 0):
        """
        Returns output for the ?queue command.
        """
        # Get the queue size.
        queue = self._play_queue._queue
        qsize = await db.get_config(self.channel.server.id, "max_queue", default=99, type_=int)

        if len(queue) != 0 and start_pos + 1 > len(queue):
            return ":x: Queue is not as long as that."
        if start_pos < 0:
            return ":x: Cannot check queue for negative numbers."

        # Set song str.
        song_str = ""
        # Set total duration.
        total_dur = 0

        # First loop over items to get the duration
        for i in queue:
            if isinstance(i[1], dict):
                total_dur += i[1].get("duration", 0)

        # Ternary of doom.
        # I'm not entirely sure what this does.
        for item in range(start_pos, start_pos + len(queue) if len(queue) < 10 else start_pos + 10):
            try:
                i = queue[item]
            except IndexError:
                break
            if isinstance(i[1], str):
                title = i[1]
                df = "??:??"
            else:
                title = i[1].get("title")
                # get duration
                dm, ds = divmod(i[1].get("duration"), 60)
                df = "`[{:02d}:{:02d}]`".format(trunc(dm), trunc(ds))
            song_str += "\n{}. `{}` `{}`".format(item + 1, title, df)

        if len(queue) > start_pos + 10:
            song_str += "\n(Omitted {} queued items.)".format((len(queue) - 10) - start_pos)

        # Divmod queue length, to get total length.
        tm, ds = divmod(total_dur, 60)
        dh, dm = divmod(tm, 60)

        s = "**Currently queued: ({lq}/{mq})** `[{h:02d}:{m:02d}:{s:02d}]`" \
            .format(lq=len(queue), mq=qsize,
                    h=trunc(dh), m=trunc(dm), s=trunc(ds))

        # Check if the queue is empty.
        if not queue or len(queue) == 0:
            s += "\n`Nothing is queued.`"
            return s

        s += song_str

        return s

    async def cmd_skip(self, to_skip: int):
        """
        Skip command implementation
        """

        # Get the max queue size
        qsize = await db.get_config(self.server.id, "max_queue", default=99, type_=int)

        if not self.playing:
            return ":x: No song is currently playing on this server."

        if not self.player:
            # Attempt to restore internal state.
            self.curr_task.cancel()
            self._play_queue = asyncio.Queue(qsize)
            await self.disconnect()
            return ":x: Inconsistent internal state - resetting connection. " \
                   "This is usually because of multiple commands at once."

        if to_skip == 1:
            # Just stop the player.
            self.player.stop()
            return ":heavy_check_mark: Skipped current song."

        # Stop the player.
        self.player.stop()

        # Remove 1 off of to_skip to represent the current song
        to_skip -= 1

        if len(self._play_queue._queue) < to_skip:
            # Reset.
            self._play_queue = asyncio.Queue(qsize)
            self.curr_task.cancel()
            self.playing = False
            self.player = None
            self.current_coroutine = None
            self.progress = 0
            self.duration = 0
            self.title = ""
            return ":heavy_check_mark: Reached end of queue."

        new_queue = asyncio.Queue(maxsize=qsize)
        for i in self._play_queue._queue[to_skip:]:
            try:
                new_queue.put_nowait(i)
            except asyncio.QueueFull:
                # if the queue-size was shrunk between playing and a skip, this might happen
                pass

        # Update the queue.
        self._play_queue = new_queue
        return ":heavy_check_mark: Skipped {} items.".format(to_skip)

    def cmd_voteskip(self, author_id: str):
        """
        Implementation of voteskip
        """
        vc_count = 0
        for member in self.channel.voice_members:
            if member.deaf or member.self_deaf:
                continue
            elif member.id == self.user.id:
                continue
            else:
                vc_count += 1

        # Divide it by two.
        required = int(ceil(vc_count / 2))

        # Voteskip.
        if author_id not in self.voteskips:
            self.voteskips.append(author_id)
        else:
            return ":x: You have already voted."

        # Skip as appropriate.
        if len(self.voteskips) >= required or required == 1:
            self.player.stop()
            self.playing = False
            self.voteskips = []
            return ":heavy_check_mark: Skipped current track."
        else:
            return ":heavy_check_mark: Voteskip acknowledged. `{}` more votes required.".format(required - len(self.voteskips))

    async def cmd_move(self, fr: int, to: int):
        """
        Implementation of move command
        """
        internal_queue = list(self._play_queue._queue)
        try:
            got = internal_queue.pop(fr)
            internal_queue.insert(to, got)
        except IndexError as e:
            return ":x: Could not find track at index `{}`."

        qsize = await db.get_config(self.server.id, "max_queue", default=99, type_=int)

        # Re-create queue, blah blah blah
        new_queue = asyncio.Queue(maxsize=qsize)

        for i in internal_queue:
            try:
                new_queue.put_nowait(i)
            except asyncio.QueueFull:
                pass

        self._play_queue = new_queue

        title = got[1].get("title")

        return ":heavy_check_mark: Moved item `{}` to position `{}`.".format(title, to)

    async def cmd_remove(self, start: int, end: int=None):
        """
        Implementation for remove.
        """
        if end is None:
            end = start

        internal_queue = list(self._play_queue._queue)

        if start > end:
            return ":x: Start must be larger than end."

        if start <= 0:
            return ":x: Cannot remove queue items less than 1."

        if start > len(internal_queue):
            return ":x: Queue is not as long as `{}`.".format(start)
        elif end > len(internal_queue):
            return ":x: Queue is not as long as `{}`.".format(end)

        try:
            for i in range(start, end + 1):
                # Pop the start item, so it stays in position each time.
                removed = internal_queue.pop(start - 1)
        except IndexError:
            # what
            pass

        qsize = await db.get_config(self.server.id, "max_queue", default=99, type_=int)

        # Re-create queue, blah blah blah
        new_queue = asyncio.Queue(maxsize=qsize)

        for i in internal_queue:
            try:
                new_queue.put_nowait(i)
            except asyncio.QueueFull:
                pass

        self._play_queue = new_queue

        # If we only removed one, return the item we removed.
        if (start == end):
            return ":heavy_check_mark: Deleted item {} `({})`.".format(start, removed[1].get("title"))
        else:
            return ":heavy_check_mark: Deleted items {} to {}.".format(start, end)

    async def cmd_shuffle(self):
        """
        Implementation of the shuffle command.
        """
        qsize = await db.get_config(self.server.id, "max_queue", default=99, type_=int)

        # Create the new Queue.
        new_queue = asyncio.Queue(maxsize=qsize)

        # Create a list of the old queue.
        deq = list(self._play_queue)

        # Shuffle it.
        random.shuffle(deq)

        # Append all items to the new queue.
        for i in deq:
            try:
                new_queue.put_nowait(i)
            except asyncio.QueueFull:
                # wat
                break

        # Update the queue.
        self._play_queue = new_queue

        return ":heavy_check_mark: Shuffled queue."

    def cmd_again(self):
        """
        Implementation of `again`.
        """
        if not self.playing:
            return ":x: Not currently playing on this server."

        # Place the coroutine on the queue, again.
        try:
            self._play_queue.put_nowait((self.coro_factory, self.curr_info))
        except asyncio.QueueFull:
            return ":x: Queue is full."

        return ":heavy_check_mark: Playing `{}` again.".format(self.title)

    async def reset(self):
        """
        Reset the voice player.
        """
        self.player.stop()
        await self.disconnect()
        self.playing = False
        self.player = None
        if self.curr_task:
            self.curr_task.cancel()