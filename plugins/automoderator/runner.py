"""
This contains the bulk of the commands.
"""
import re

import yaml

from navalbot.api.commands import CommandContext
from plugins.automoderator.obb import Action

matcher = re.compile(r"```(.*)```", re.S)


def _extract_yaml(data: str) -> dict:
    """
    Load the YAML out of the string.
    """
    matched = matcher.findall(data)
    if matched:
        ym = yaml.safe_load_all(matched[0])
    else:
        return None
    return ym


async def apply(ctx: CommandContext):
    """
    Applies an action to be run.
    """
    # Extract the YAML.
    data = _extract_yaml(' '.join(ctx.args[1:]))
    if not data:
        await ctx.reply("automod.no_data")
        return

    # Get the `mod` element.
    for doc in data:
        root = doc.get("mod")
        if not root:
            await ctx.reply("automod.no_mod")
            continue

        # Construct the command to apply.
        parsed = Action(root)
        await parsed.run(ctx)
