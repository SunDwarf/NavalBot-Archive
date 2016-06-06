import asyncio
import logging

logger = logging.getLogger("AsyncMeta")

loop = asyncio.get_event_loop()


class _AsyncMeta(type):
    """
    Metaclass that allows you to have an async __init__.
    """

    def __call__(cls, *args, **kwargs):
        # Manually call __init__
        logger.info("Creating async class `{}`".format(cls.__name__))
        coro = cls.__init__(cls, *args, **kwargs)
        # Ensure it.
        asyncio.ensure_future(coro, loop=loop)
        return cls


class AsyncClass(metaclass=_AsyncMeta):
    """
    Stub class that can be inherited from to get AsyncMeta.
    """
