import os
import random
import re
import sqlite3

import aiohttp
import discord

import red

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
    cursor.execute("SELECT (value) FROM configuration WHERE configuration.name = 'game'")
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

    if message.author.permissions_in(message.channel).manage_roles and len(game) < 64:
        # user has perms
        await client.change_status(game=discord.Game(name=game))
        await client.send_message(message.channel, "Changed game to `{}`".format(game))
        # save it in the DB
        cursor.execute("""INSERT OR REPLACE INTO configuration (id, name, value)
                      VALUES ((SELECT id FROM configuration WHERE name = 'game'), 'game', ?)""", (game,))
        db.commit()

    else:
        await client.send_message(message.channel,
                                  "You don't have the right role for this or the entered name was too long")


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
    fac = message.content.split(' ')[1]
    # check if it's locked
    cursor.execute("SELECT locked, locker FROM factoids WHERE name = ?", (fac,))
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
        cursor.execute("SELECT locked, locker FROM factoids WHERE factoids.name = ?", (name,))
        row = cursor.fetchone()
        if row:
            locked, locker = row
            print(locker, message.author.id, locker == message.author.id)
            if locked and locker != message.author.id:
                await client.send_message(message.channel, "Cannot change factoid `{}` locked by `{}`"
                                          .format(name, locker))
                return
        cursor.execute("INSERT OR REPLACE "
                       "INTO factoids (id, name, content) "
                       "VALUES ((SELECT id FROM factoids WHERE name = ?), ?, ?)", (name, name, fac))
        db.commit()
        await client.send_message(message.channel, "Factoid `{}` is now `{}`".format(name, fac))
    else:
        # Get factoid
        cursor.execute("SELECT (content) FROM factoids WHERE factoids.name = ?", (data,))
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


async def guess(client: discord.Client, message: discord.Message):
    await client.send_message(message.channel, "Number Game:\nEnter a number between 1 and 10")

    def guess_check(m):
        return m.content.isdigit()

    guess = await client.wait_for_message(timeout=5.0, author=message.author, check=guess_check)
    answer = random.SystemRandom().randrange(1, 10)
    if guess is None:
        botmsg = 'Sorry, you waited to long, the answer was {}'.format(answer)
        await client.send_message(message.channel, botmsg)
        return
    if int(guess.content) == answer:
        await client.send_message(message.channel, 'Nice, you guessed the right number!')
    else:
        await client.send_message(message.channel, 'Sorry. It was {}'.format(answer))


async def commands(client: discord.Client, message: discord.Message):
    com = ['-game', '-lock', '-guess', '-reddit', '-private']
    await client.send_message(message.channel, "These commands are available:\n{}".format('\n'.join(com)))


async def reddit(client: discord.Client, message: discord.Message):
    try:
        choice = ' '.join(message.content.split(" ")[1:])
        await client.send_message(message.channel, 'The top posts from {} have been sent to you'.format(choice))
        red_fetched = red.main(userchoice=choice)
        for link in red_fetched:
            await client.send_message(message.author, content=link)
    except TypeError as f:
        print('[ERROR]', f)


async def private(client: discord.Client, message: discord.Message):
    await client.send_message(message.author, content='Whatsup, you called me?')


async def kick(client: discord.Client, message: discord.Message):
    try:
        if message.author.permissions_in(message.channel).manage_roles:
            await client.kick(member=message.mentions[0])
            await client.send_message(message.channel,
                                      '{} got kicked by {}!'.format(message.mentions[0], message.author.name))
        else:
            await client.send_message(message.channel, "You don't have the right role for this!")
    except discord.Forbidden as forbidden:
        print('Forbidden', forbidden)


async def ban(client: discord.Client, message: discord.Message):
    try:
        if message.author.permissions_in(message.channel).manage_roles:
            await client.ban(member=message.mentions[0])
            await client.send_message(message.channel,
                                      '{} got banned by {}!'.format(message.mentions[0], message.author.name))
        else:
            await client.send_message(message.channel, "You don't have the right role for this!")
    except discord.Forbidden as forbidden:
        print('Forbidden: ', forbidden)


async def unban(client: discord.Client, message: discord.Message):
    await client.send_message(message.channel, 'Lol, unbans')
