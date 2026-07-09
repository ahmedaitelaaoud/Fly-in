class ParsingErrors(Exception):
    pass


class HubException(ParsingErrors):
    pass


class ConnectionException(ParsingErrors):
    pass


class DronesException(ParsingErrors):
    pass
