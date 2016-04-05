import discord


def with_permission(role: str):
    """
    Only allows a command with permission.
    """
    def __decorator(func):
        async def __fake_func(client: discord.Client, message: discord.Message):
            # Get the user's roles.
            try:
                assert isinstance(message.author, discord.Member)
            except AssertionError:
                await client.send_message(message.channel, ":no_entry: Cannot determine your role!")
                return
            roles = message.author.roles
            has_role = discord.utils.get(roles, name=role)
            if has_role:
                await func(client, message)
            else:
                await client.send_message(message.channel,
                                          ":no_entry: You do not have the required role: `{}`!".format(role))

        return __fake_func
    return __decorator
