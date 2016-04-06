import asyncio
import discord
import aiohttp
import util


async def check_for_commits(client: discord.Client):
    """
    This isn't decorated with a command, as it runs within a loop.
    """
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
    else:
        chan_id = int(chan_id)

    # Find the channel.
    for server in client.servers:
        assert isinstance(server, discord.Server)
        # Find the channel specified by the ID.
        chan = server.get_channel(chan_id)
        if chan:
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
               "User-Agent": "NavalBot Commit Module v1.0 Arbitrary Number"}

    # Define the last etag.
    etag = ""

    # Enter the client session.
    with session:
        while True:
            await asyncio.sleep(5)  # Sleep for 5 seconds between requests.
            # Get the repo details.
            async with session.get("https://api.github.com/repos/{}/events".format(repo),
                                   headers={**headers, **{"If-None-Match": etag}}) as r:
                # Save the e-tag.
                assert isinstance(r, aiohttp.ClientResponse)
                if r.status == 304:
                    continue
                etag = r.headers["ETag"]

                # Load the