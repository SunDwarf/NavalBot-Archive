"""
NavalBot testing suite.
"""
import asyncio
import warnings

import pytest

import discord
from navalbot.api.botcls import NavalClient
from navalbot.api.locale import get_locale
from navalbot.testing.test_client import TestClient

# Silence warnings.
warnings.warn = lambda *args, **kwargs: "Fuck off"

# This will raise an ImportError.
# To fix, dump a GUILD_CREATE event and write it to file with the variable `ev`.
# Also, add a MESSAGE object object under `msg`.
# Make sure it's in the same server.
import guild_data_dump

# Create some example data.
testing_server = discord.Server(**guild_data_dump.ev["d"])
testing_channel = testing_server.default_channel

# Test messages.
test_msg = discord.Message(**guild_data_dump.msg["d"])
test_msg.server = testing_server
test_msg.channel = testing_channel

tc = TestClient(None)

member = discord.utils.get(testing_server.members, name=tc.config.get("test_user", None))
if member:
    # Not strictly a user, but oh well.
    # We're testing -> We don't care.
    user = member
else:
    user = list(testing_server.members)[0]

# Create the test client.
tc.user = user
# Set the instance of the bot.
NavalClient._instance = tc


@pytest.mark.asyncio
async def test_on_ready(event_loop):
    """
    Test on_ready firing.
    """
    with tc:
        await tc.fire_event("on_ready")
        data = tc.collect("change_status")
        assert isinstance(data, discord.Game)
        assert data.name == "Type ?info for help!"


def test_locale_loader():
    """
    Tests a the LocaleLoader.
    """
    loc = get_locale(None)
    assert loc["some-bad-key"] == "some-bad-key"
    assert loc.get("some-bad-key") is None
    assert loc["generic.not_int"] == ":x: Value {val} is not a valid integer."


@pytest.mark.asyncio
async def test_some_message(event_loop):
    with tc:
        await tc.fire_event("on_message", test_msg)
        # No data should be returned for our sample message.
        assert tc.collect("send_message") is None


@pytest.mark.asyncio
async def test_command_firing(event_loop):
    """
    Test commands fire by running a very basic command.
    """
    with tc:
        test_msg.content = "?fullwidth abc"
        await tc.fire_event("on_message", test_msg)
        results = tc.collect("send_message")
        assert tc.errored is False
        assert results[0][1] == "ａｂｃ"
