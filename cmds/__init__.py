commands = {}


def command(name):
    """
    Register a new command.
    """

    def __decorator(func):
        commands[name] = func
        return func

    return __decorator