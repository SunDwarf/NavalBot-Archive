"""
Modified client for testing.

Mocks a lot of things.
"""
import sys

import logbook
from logbook.handlers import Handler

import discord
from ..api.botcls import NavalClient


class TestClient(NavalClient):
    """
    Mock client.

    Events are called with `.fire_event()`.
    Actions are collected with `.collect(action)`, i.e `.collect("send_message")`.
    """

    def __init__(self, user: discord.User, *args, **kwargs):
        # Override sys.argv so that it loads `test.yml`.
        if len(sys.argv) >= 2:
            sys.argv[1] = "test_client.yml"
        else:
            sys.argv.append("test_client.yml")
        super().__init__(*args, **kwargs)

        # Manually set our `self.user`, as it won't exist normally.
        # This should be provided as a user object, as we can't get one as we never connect to Discord.
        self.user = user

        # Collected event data.
        # This is used for the tests to collect after firing an event.
        self._collected_event_data = {}

        # Set testing to `True` so db knows to re-create the pool.
        self.testing = True

        # Nuke logging.
        logbook.Handler.handle = lambda *args, **kwargs: None

    def __new__(cls, *args, **kwargs):
        return object.__new__(cls)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._collected_event_data.clear()

    async def fire_event(self, event_name, *args, **kwargs):
        """
        Fires an event on the test client.
        """
        self.errored = False
        coro = getattr(self, event_name)(*args, **kwargs)
        try:
            result = await coro
            self.errored = False
            return result
        except Exception as e:
            self.errored = e

    def collect(self, action):
        """
        Get event data for the specified action.

        This is automatically pooled by the actions when running.
        """
        if self.errored:
            self.errored = False
            raise self.errored

        return self._collected_event_data.get(action)

    async def change_status(self, game=None, idle=False):
        self._collected_event_data["change_status"] = game

    async def send_message(self, destination, content, *, tts=False):
        """
        Capture a send_message event.
        """
        if not self._collected_event_data.get("send_message"):
            self._collected_event_data["send_message"] = []
        self._collected_event_data["send_message"].append((destination, content))
