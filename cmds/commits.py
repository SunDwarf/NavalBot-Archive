import asyncio
from datetime import datetime

import discord
import aiohttp
import util


async def check_for_commits(client: discord.Client):
    """
    This isn't decorated with a command, as it runs within a loop.
    """
    print("==> Loaded CommitBot.")
    # First, check to see if we're enabled.
    gh_enabled = util.get_config("github_enabled", 0)
    if not int(gh_enabled):
        return

    # Get the token.
    token = util.get_config("github_token")
    if not token:
        print("==> GitHub commit bot token doesn't exist. Cannot use commit module.")
        return

    # Get the channel ID.
    chan_id = util.get_config("github_channel")
    if not chan_id:
        print("==> Cannot resolve channel for CommitBot.")
        return

    # Find the channel.
    for server in client.servers:
        assert isinstance(server, discord.Server)
        # Find the channel specified by the ID.
        chan = server.get_channel(chan_id)
        if chan:
            print("==> CommitBot got channel: {}".format(chan.name))
            break
    else:
        print("==> Cannot resolve channel for CommitBot. (could not find the channel with id {})".format(chan_id))
        return

    repo = util.get_config("github_repo")
    if not repo:
        print("==> Cannot resolve repository for CommitBot.")
        return

    # Load up an aiohttp session.
    session = aiohttp.ClientSession()

    # Define the custom authorization header.
    headers = {"Authorization": "token {}".format(token),
               "User-Agent": "NavalBot Commit Module v1.0 Arbitrary Number",
               "Time-Zone": "Etc/UTC"}  # Force the UTC time zone.

    # Define the last time.
    last_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # Enter the client session.
    with session:
        while True:
            await asyncio.sleep(5)  # Sleep for 5 seconds between requests.
            # Get the repo details.
            async with session.get("https://api.github.com/repos/{}/commits".format(repo),
                                   headers=headers, params={"since": last_time}) as r:
                # Save the last access time.
                assert isinstance(r, aiohttp.ClientResponse)
                # Next, JSON decode the body.
                body = await r.json()
                if len(body) == 0:
                    continue
                else:
                    last_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                # Create the head of a message
                await client.send_message(chan, "**{} new commits to** *{}*:\n".format(len(body), repo))
                # Loop over the commits.
                for commit in body:
                    print(commit)
                    # Create a message.
                    await client.send_message(
                        chan,
                        "**{data['commit']['sha'][0:10]}**: {data['commit']['message']}\n".format(data=commit) +
                        "by *{data['commit']['committer']['name']".format(data=commit)
                    )
