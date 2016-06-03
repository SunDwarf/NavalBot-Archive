"""
Plugin for overwatch stuff.
"""
import logging

from navalbot.api.commands import command, CommandContext
import aiohttp

OWAPI_BASE_URL = "https://owapi.net"

logger = logging.getLogger("NavalBot")


async def get_profile_json(btag: str, endpoint: str = "stats") -> dict:
    """
    Get the profile JSON using owapi.
    """
    url = OWAPI_BASE_URL + "/api/v1/u/{}/{}".format(btag, endpoint)
    logger.info("GET => {}".format(url))
    async with aiohttp.ClientSession() as sess:
        async with sess.get(OWAPI_BASE_URL + "/api/v1/u/{}/{}".format(btag, endpoint)) as r:
            assert isinstance(r, aiohttp.ClientResponse)
            if r.status != 200:
                # Usually a 404.
                return None
            return await r.json()


async def get_stats_formatted(btag: str) -> str:
    """
    Gets the formatted stats output of a user.
    """
    # First, get the stats endpoint.
    st = await get_profile_json(btag, endpoint="stats")
    if st is None:
        return None

    base = """Stats for user `{btag}`:
```xl
Games: {games}
Wins: {wins}  /  Losses: {losses}  / Win rate: {wr}%
Rank: #{rank}

Game stats:
{gst}

Top 5 heroes:
{hst}
```"""
    # Build the two formatted strings.
    gst = ""
    for stat in st["game_stats"]:
        gst += "{}: {} AVG / {} Total\n".format(stat["name"].capitalize(),
                                                stat["avg"] if stat["avg"] is not None else "N/A",
                                                stat["value"])

    # Build the hero string.
    hero_data = await get_profile_json(btag, endpoint="heroes")
    if not hero_data:
        hst = "??? Error on fetching hero stats."
    else:
        hero_list = []
        for n, hero in enumerate(hero_data["heroes"]):
            h_built = "#{} - {} - {} Games / {}% Win rate - {} average KPD - {} hours".format(
                n + 1, hero["name"].capitalize(), hero["games"], hero["winrate"], hero["kpd"], hero["hours"]
            )
            hero_list.append(h_built)
        hst = "\n".join(hero_list)

    # Format the base string.
    overall = st["overall_stats"]
    built = base.format(btag=btag, games=overall["games"], wins=overall["wins"], losses=overall["losses"],
                        rank=overall["rank"], wr=overall["win_rate"], gst=gst, hst=hst)

    return built


@command("ow", "overwatch", argcount="+")
async def get_ow_profile_data(ctx: CommandContext):
    """
    Gets profile data about a user.
    """
    if ctx.args and len(ctx.args) > 0:
        # Check if it's a user.
        u = ctx.get_user()
        if u:
            # Load the battletag from the DB.
            btag = await ctx.db.get_key("overwatch:{}".format(u.id))
            if not btag:
                btag = "???"
        else:
            # Assume it's a battletag.
            btag = ctx.args[0]
    else:
        btag = await ctx.db.get_key("overwatch:{}".format(ctx.author.id))

    if btag is None:
        await ctx.reply("ow.btag_not_set")

    # Build the stats.
    stats = await get_stats_formatted(btag)
    if not stats:
        await ctx.reply("ow.no_such_btag", btag=btag)
    else:
        await ctx.client.send_message(ctx.channel, stats)


@command("setbtag", argcount=1)
async def setbtag(ctx: CommandContext):
    """
    Sets your battletag.
    """
    btag = ctx.args[0].replace("#", "-")
    await ctx.db.set_key("overwatch:{}".format(ctx.author.id), btag)
    await ctx.reply("ow.set_btag", btag=btag)


@command("getbtag", argcount="?")
async def getbtag(ctx: CommandContext):
    """
    Gets a battletag.
    """
    user = ctx.get_user() or ctx.author
    btag = await ctx.db.get_key("overwatch:{}".format(ctx.author.id))

    if btag is None:
        await ctx.reply("ow.btag_not_set")
        return

    await ctx.client.send_message(ctx.message.channel, btag)