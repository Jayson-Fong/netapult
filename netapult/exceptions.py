class NetapultBaseException(Exception):
    pass


class DispatchException(NetapultBaseException):
    pass


class UnknownModeException(NetapultBaseException):
    pass


class PromptNotFoundException(NetapultBaseException):
    pass
