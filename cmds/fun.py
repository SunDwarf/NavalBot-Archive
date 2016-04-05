import discord
import pyowm
from google import search

import cmds
import nsfw
import red


@cmds.command("private")
async def private(client: discord.Client, message: discord.Message):
    await client.send_message(message.author, content='Whatsup, you called me?')


@cmds.command("google")
async def google(client: discord.Client, message: discord.Message):
    userinput = ' '.join(message.content.split(" ")[1:])
    await client.send_message(message.channel, "The links have been sent to you {}".format(message.author))
    for url in search(userinput, stop=2):
        await client.send_message(message.author, url)


@cmds.command("weather")
async def weather(client: discord.Client, message: discord.Message):
    owm = pyowm.OWM('9f74a3874a03fd3d9a30cdd64b652b5c')  # Example API-Key
    try:
        userinput = ' '.join(message.content.split(" ")[1:])
        # Get it from the place
        observation = owm.weather_at_place(userinput)
        # Get the weather and stuff.
        w = observation.get_weather()
        w.get_wind()
        wind = w.get_wind()['speed']
        humidity = w.get_humidity()
        temp = w.get_temperature('celsius')['temp']
        await client.send_message(
            message.channel,
            '☁__Weather for {}:__\n** Temperature:** {} °C **Humidity:** {} % **Wind:** {} m/s'
                .format(userinput, temp, humidity, wind)
        )
    except AttributeError:
        await client.send_message(message.channel, "This city does not exist")


@cmds.command("commands")
async def commands(client: discord.Client, message: discord.Message):
    com = ['-lock', '-guess', '-reddit', '-private', '-servers', '-version', '-weather', '\n**Admins only:**',
           '-game', '-kick', '-ban', '-unban', '-mute', '-unmute', '-delete']
    await client.send_message(message.channel, "**These commands are available:**\n{}".format('\n'.join(com)))


@cmds.command("reddit")
async def reddit(client: discord.Client, message: discord.Message):
    try:
        choice = ' '.join(message.content.split(" ")[1:]).lower()
        if choice in nsfw.PURITAN_VALUES:
            await client.send_message(message.channel, 'You´re not supposed to search for this ಠ_ಠ')
        else:
            await client.send_message(message.channel, 'The top posts from {} have been sent to you'.format(choice))
            red_fetched = red.main(userchoice=choice)
            for link in red_fetched:
                await client.send_message(message.author, content=link)
    except TypeError as f:
        print('[ERROR]', f)
