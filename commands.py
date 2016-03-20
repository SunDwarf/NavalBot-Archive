import os
import re
import sqlite3

import aiohttp

import discord

factoid_matcher = re.compile(r'(.*?) is (.*)')

# Get DB
db = sqlite3.connect("navalbot.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS factoids (
  id INTEGER PRIMARY KEY, name VARCHAR, content VARCHAR, locked INTEGER, locker VARCHAR
);
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS configuration (
  id INTEGER PRIMARY KEY,
  name VARCHAR,
  value VARCHAR
)
""")

async def on_ready(client: discord.Client):
    # Set the current game, as saved.
    cursor.execute("select (value) from configuration where configuration.name = 'game'")
    result = cursor.fetchone()
    if not result:
        # Ignore.
        return
    else:
        game = result[0]
        await client.change_status(game=discord.Game(name=game))

async def game(client: discord.Client, message: discord.Message):
    # Set my game
    game = ' '.join(message.content.split(" ")[1:])

    if message.author.permissions_in(message.channel).manage_roles:
        # user has perms
        await client.change_status(game=discord.Game(name=game))
        await client.send_message(message.channel, "Changed game to `{}`".format(game))
        # save it in the DB
        cursor.execute("""insert or replace into configuration (id, name, value)
                      values ((select id from configuration where name = 'game'), 'game', ?)""", (game, ))
        db.commit()

    else:
        await client.send_message(message.channel, "You don't have the right role for this")

async def sql(client: discord.Client, message: discord.Message):
    if not int(message.author.id) == 141545699442425856:
        await client.send_message(message.channel, "You're not Sun")
        return
    else:
        sql_cmd = ' '.join(message.content.split(' ')[1:])
        cursor.execute(sql_cmd)

async def py(client: discord.Client, message: discord.Message):
    if not int(message.author.id) == 141545699442425856:
        await client.send_message(message.channel, "You're not Sun")
        return
    else:
        cmd = ' '.join(message.content.split(' ')[1:])
        exec(cmd)

async def lock(client: discord.Client, message: discord.Message):
    # get factoid
    fac = ' '.join(message.content.split(' ')[1:])
    # check if it's locked
    cursor.execute("select locked, locker from factoids where name = ?", (fac, ))
    row = cursor.fetchone()
    if row:
        if row[0] and row[1] != message.author.id:
            await client.send_message(message.channel, "Cannot change factoid `{}` locked by `{}`"
                                          .format(fac, row[1]))
            return
    else:
        await client.send_message(message.channel, "Factoid `{}` does not exist".format(fac))
        return
    # Update factoid to be locked
    cursor.execute("""UPDATE factoids SET locked = 1, locker = ? WHERE name = ?""",
                   (str(message.author.id), fac))
    db.commit()
    await client.send_message(message.channel, "Factoid `{}` locked to ID `{}` ({})".format(fac, message.author.id,
                                                                                            message.author.name))

async def get_file(client: tuple, url, name):
    """
    Get a file from the web using aiohttp, and save it
    """
    with aiohttp.ClientSession() as sess:
        async with sess.get(url) as get:
            assert isinstance(get, aiohttp.ClientResponse)
            if int(get.headers["content-length"]) > 1024 * 1024 * 8:
                # 1gib
                await client[0].send_message(client[1].channel, "File {} is too big to DL")
                return
            else:
                data = await get.read()
                with open(os.path.join(os.getcwd(), 'files', name), 'wb') as f:
                    f.write(data)
                print("--> Saved file to {}".format(name))


def sanitize(param):
    param = param.replace('..', '.').replace('/', '')
    param = param.split('?')[0]
    return param


async def default(client: discord.Client, message: discord.Message):
    data = message.content[1:]
    # Check if it matches a factoid creation
    matches = factoid_matcher.match(data)
    if matches:
        # Set the factoid
        name = matches.groups()[0]
        fac = matches.groups()[1]
        assert isinstance(fac, str)
        if fac.startswith("http"):
            # download as a file
            file = sanitize(fac.split('/')[-1])
            client.loop.create_task(get_file((client, message), url=fac, name=file))
            fac = "file:{}".format(file)
        # check if locked
        cursor.execute("select locked, locker from factoids where factoids.name = ?", (name,))
        row = cursor.fetchone()
        if row:
            locked, locker = row
            print(locker, message.author.id, locker == message.author.id)
            if locked and locker != message.author.id:
                await client.send_message(message.channel, "Cannot change factoid `{}` locked by `{}`"
                                          .format(name, locker))
                return
        else:
            locked, locker = 0, ""
        cursor.execute("""insert or replace into factoids (id, name, content, locked, locker)
                          values ((select id from factoids where name = ?), ?, ?, ?, ?)""",
                       (name, name, fac, locked, locker))

        db.commit()
        await client.send_message(message.channel, "Factoid `{}` is now `{}`".format(name, fac))
    else:
        # Get factoid
        cursor.execute("select (content) from factoids where factoids.name = ?", (data,))
        rows = cursor.fetchone()
        if not rows:
            return
        # Load content
        content = rows[0]
        assert isinstance(content, str)
        # Check if it's a file
        if content.startswith("file:"):
            fname = content.split("file:")[1]
            if not os.path.exists(os.path.join(os.getcwd(), 'files', fname)):
                await client.send_message(message.channel, "This kills the bot")
                return
            # Load the file
            with open(os.path.join(os.getcwd(), 'files', fname), 'rb') as f:
                await client.send_file(message.channel, f)
            return
        await client.send_message(message.channel, content)