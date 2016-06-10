"""
Automoderator commands.
"""
from navalbot.api.commands import command, CommandContext
from navalbot.api.commands.cmdclass import NavalRole

from . import runner


@command("automod", "automoderator", roles={NavalRole.ADMIN}, argcount="+", force_split=True)
async def automoderator(ctx: CommandContext):
    """
    Automoderator base command.
    """
    try:
        base_command = ctx.args[0]
    except IndexError:
        await ctx.reply("automod.no_subcommand")
        return

    # Switch based on the base command.
    if base_command == "apply":
        await runner.apply(ctx)
