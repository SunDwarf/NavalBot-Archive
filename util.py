import sqlite3

import discord

db = sqlite3.connect("navalbot.db")
cursor = db.cursor()


def get_config(key: str):
    """
    Gets a config value from the DB.
    """
    cursor.execute("""SELECT value FROM configuration WHERE name = ?""", (key,))
    row = cursor.fetchone()
    return row


def set_config(key: str, value: str):
    cursor.execute("INSERT OR REPLACE "
                   "INTO configuration (id, name, value)"
                   "VALUES ((SELECT id FROM factoids WHERE name = ?), ?, ?)", (key, key, value))
    db.commit()


def with_permission(*role: str):
    """
    Only allows a command with permission.
    """
    role = set(role)

    def __decorator(func):
        async def __fake_func(client: discord.Client, message: discord.Message):
            # Get the user's roles.
            try:
                assert isinstance(message.author, discord.Member)
            except AssertionError:
                await client.send_message(message.channel, ":no_entry: Cannot determine your role!")
                return
            roles = set([r.name for r in message.author.roles])
            print(roles, role)
            if roles.intersection(role):
                await func(client, message)
            else:
                await client.send_message(message.channel,
                                          ":no_entry: You do not have any of the required roles: `{}`!".format(role))

        return __fake_func

    return __decorator
