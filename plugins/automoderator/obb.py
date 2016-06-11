"""
AutoModerator object class.

Used for running.
"""
import discord

from navalbot.api.commands import CommandContext


class NoSuchItem(Exception): ...


class Action(object):
    """
    Represents an action to run.
    """

    def __init__(self, ctx: CommandContext, doc: dict):
        """
        Defines a new moderation Action.
        """
        self._document = doc

        self._ctx = ctx

        self.items = {"users": [], "channels": [], "permissions": [], "roles": [], "attrs": {}}

        # Parse it out.
        self._parse_action()

    def _parse_action(self):
        """
        Parses the action and creates the appropriate data fields.
        """
        self.action = self._document.get("action")

        # Parse out the items.
        self._items = self._document.get("items", [])

        # Parse them into objects.
        self._parse_items()

        # Parse the permissions.
        self._perms = self._document.get("permissions", [])
        self._parse_permissions()

    def _parse_permissions(self):
        """
        Parse out the permissions.
        """
        if isinstance(self._perms,  int):
            # Integer role, create a new permissions object for it.
            self.items["permissions"] = discord.Permissions(permissions=self._perms)
        elif isinstance(self._perms, list):
            # Get each item, and setattr it.
            self.items["permissions"] = discord.Permissions()
            for perm in self._perms:
                setattr(self.items["permissions"], perm, True)
        else:
            self.items["permissions"] = discord.Permissions.none()

    def _parse_items(self):
        """
        Parses out the items in self._items and loads them.
        """
        for item in self._items:
            # Str items, for example, users.
            if isinstance(item, str):
                # If it begins with an `!`, it's a user.
                if item.startswith("!"):
                    u = self._ctx.get_named_user(item[1:])
                    if not u:
                        raise NoSuchItem(item[1:])
                    self.items["users"].append(u)
                # If it starts with a `#`, it's a channel.
                if item.startswith("#"):
                    assert isinstance(self._ctx.server, discord.Server)
                    # Check for the special case @all.
                    if item == "#@all":
                        for chan in self._ctx.server.channels:
                            self.items["channels"].append(chan)
                    else:
                        chan = discord.utils.get(self._ctx.server.channels, name=item[1:])
                        if not chan:
                            raise NoSuchItem(item[1:])
                        self.items["channels"].append(chan)
                # If it starts with a `@`, it's a role
                if item.startswith("@"):
                    r = discord.utils.get(self._ctx.server.roles, name=item[1:])
                    if not r:
                        raise NoSuchItem(item[1:])
                    self.items["roles"].append(r)
            # Dict items, for stuff like create-role.
            elif isinstance(item, dict):
                self.items["attrs"].update(item)

    async def action_mute(self):
        """
        Runs a mute action.
        """
        users = self.items["users"]
        channels = self.items["channels"]
        # Mute the specified users on the specified channels.
        perms = discord.Permissions.text()
        # Give them some perms, like read.
        perms.read_messages = True
        perms.read_message_history = True
        for user in users:
            for chan in channels:
                assert isinstance(user, discord.User)
                assert isinstance(chan, discord.Channel)
                await self._ctx.client.edit_channel_permissions(chan, user, deny=perms)
                await self._ctx.reply("automod.actions.mute", chan=chan.name, user=user.display_name)

    async def action_clean_perms(self):
        # Clear special permissions on each channel.
        items = self.items["users"] + self.items["roles"]
        channels = self.items["channels"]
        for item in items:
            for chan in channels:
                assert isinstance(item, (discord.User, discord.Role))
                assert isinstance(chan, discord.Channel)
                await self._ctx.client.delete_channel_permissions(chan, item)
                await self._ctx.reply("automod.actions.clean_perms", chan=chan, user=item.name)

    async def action_create_role(self):
        """
        Create role action.
        """
        attrs = self.items["attrs"]
        # Create a new role.
        # Load the attrs from self.items["attrs"]
        name = attrs.get("name", None)
        if not name:
            raise NoSuchItem("Name is not specified in items")
        colour = attrs.get("colour", 0)
        try:
            if isinstance(colour, str):
                colour = int(colour, 16)
            colour = discord.Colour(colour)
        except ValueError:
            await self._ctx.reply("generic.not_int", val=colour)
            return
        # Create the role.
        role = await self._ctx.client.create_role(self._ctx.server, name=name, colour=colour,
                                                  hoist=attrs.get("hoist", False),
                                                  permissions=self.items["permissions"])
        await self._ctx.reply("automod.actions.role_create", serv=self._ctx.server, name=name)
        # Move it if you want.
        try:
            pos = int(attrs.get("position", 0))
        except ValueError:
            await self._ctx.reply("generic.not_int", val=attrs.get("position"))
            return
        if pos:
            await self._ctx.client.move_role(self._ctx.server, role=role, position=pos)
            await self._ctx.reply("automod.actions.move_role", role=name, pos=pos)

    async def action_assign_role(self):
        """
        Assigns a role to a user.
        """
        if len(self.items["roles"]) < 1:
            await self._ctx.reply("generic.no_role_provided")
            return

        for u in self.items["users"]:
            assert isinstance(u, discord.User)
            # Assign a role to the user
            await self._ctx.client.add_roles(u, *self.items["roles"])
            await self._ctx.reply("automod.actions.add_role", user=u.name,
                                  roles=", ".join([r.name for r in self.items["roles"]]))

    async def run(self):
        """
        Runs the Automod action.
        """
        try:
            await getattr(self, "action_{}".format(self.action.replace("-", "_")))()
        except AttributeError:
            await self._ctx.reply("automod.actions.none", action=self.action)