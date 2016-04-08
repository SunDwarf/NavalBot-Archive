# NavalBot 1.8

A bot for discord servers using [discord.py] (https://github.com/Rapptz/discord.py)

[Discord Server Requirements] (https://github.com/SunDwarf/NavalBot/blob/develop/requirements.txt)

## Download and Installation

1. Download the latest release from [the releases page] (https://github.com/sundwarf/navalbot/releases/latest)  
2. Put the files (unzipped if you downloaded the .zip) in a new folder on your computer.  
3. Open up `bot.py` and change `RCE_IDS` to match your Discord user id.  

Next, open your command line and launch `bot.py` with the login credentials for your bot.  
E.g: `>> python35 bot.py youremail@address.com yourpassword`

## Configuration

Make sure to create a `Bot Commander` role and assign it to your Discord moderators/admins.  
Members with the `Bot Commander` role can execute specifc commands that are inaccessible for regular members.  
Your bot needs the `Admin` flag in order for moderation commands like `?kick` or `?ban` to work.  

## Available commands
### Commands
- [Regular commands] (#regular-commands)
- [Music commands] (#music-commands)
- [Moderation commands] (#moderation-commands)
- [Admin/Configuration commands] (#admin-commands)

#### Regular commands:

- ?commands
- ?help
- ?choice
- ?coin
- ?uptime
- ?version
- ?weather
- ?whois
- ?google
- ?info
- ?invite
- ?stats
- ?lock
- ?reddit
- ?searchyt

#### Music commands:
- ?joinvoice
- ?leavevoice
- ?nowplaying
- ?np
- ?playfile
- ?playyoutube
- ?playyt
- ?stop

#### Moderation commands
- ?mute
- ?unmute
- ?kick
- ?ban
- ?unban
- ?game
- ?delete

#### Admin commands:
- ?setcfg
- ?getcfg
- ?sql
- ?py
- ?update

## Contributing

If you'd like to contribute to Navalbot, you can:

 - [Fork the repository] (https://github.com/SunDwarf/NavalBot/fork)
 - [Create a pull request] (https://github.com/SunDwarf/NavalBot/pull/new)
 - [Create a new issue] (https://github.com/SunDwarf/NavalBot/issues/new)
 

## License

```
This program is free software: you can redistribute it and/or modify  
it under the terms of the GNU General Public License as published by  
the Free Software Foundation, either version 3 of the License, or  
(at your option) any later version.  

This program is distributed in the hope that it will be useful,  
but WITHOUT ANY WARRANTY; without even the implied warranty of  
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the  
GNU General Public License for more details.  

You should have received a copy of the GNU General Public License  
along with this program.  If not, see <http://www.gnu.org/licenses/>.  
```
