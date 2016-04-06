import sqlite3
import datetime
import time

import discord
from math import floor

db = sqlite3.connect("navalbot.db")
cursor = db.cursor()

startup = datetime.datetime.fromtimestamp(time.time())


def format_timedelta(value, time_format="{days} days, {hours2}:{minutes2}:{seconds2}"):
    if hasattr(value, 'seconds'):
        seconds = value.seconds + value.days * 24 * 3600
    else:
        seconds = int(value)

    seconds_total = seconds

    minutes = int(floor(seconds / 60))
    minutes_total = minutes
    seconds -= minutes * 60

    hours = int(floor(minutes / 60))
    hours_total = hours
    minutes -= hours * 60

    days = int(floor(hours / 24))
    days_total = days
    hours -= days * 24

    years = int(floor(days / 365))
    years_total = years
    days -= years * 365

    return time_format.format(**{
        'seconds': seconds,
        'seconds2': str(seconds).zfill(2),
        'minutes': minutes,
        'minutes2': str(minutes).zfill(2),
        'hours': hours,
        'hours2': str(hours).zfill(2),
        'days': days,
        'years': years,
        'seconds_total': seconds_total,
        'minutes_total': minutes_total,
        'hours_total': hours_total,
        'days_total': days_total,
        'years_total': years_total,
    })


def get_config(key: str) -> str:
    """
    Gets a config value from the DB.
    """
    cursor.execute("""SELECT value FROM configuration WHERE name = ?""", (key,))
    row = cursor.fetchone()
    if row:
        return row[0]
    else:
        return None


def set_config(key: str, value: str):
    cursor.execute("INSERT OR REPLACE "
                   "INTO configuration (id, name, value)"
                   "VALUES ((SELECT id FROM configuration WHERE name = ?), ?, ?)", (key, key, value))
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
            if roles.intersection(role):
                await func(client, message)
            else:
                await client.send_message(message.channel,
                                          ":no_entry: You do not have any of the required roles: `{}`!".format(role))

        return __fake_func

    return __decorator


def only(ids):
    """
    Only allows a specific set of IDs to run the command.
    """
    if isinstance(ids, int):
        ids = [ids]

    def __decorator(func):
        async def __fake_permission_func(client: discord.Client, message: discord.Message):
            # Get the ID.
            u_id = int(message.author.id)
            # Check if it is in the ids specified.
            if u_id in ids:
                await func(client, message)
            else:
                await client.send_message(message.channel,
                                          ":no_entry: This command is restricted to bot owners!")

        return __fake_permission_func
    return __decorator
