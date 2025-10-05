import abc


class NetapultBaseException(Exception, abc.ABC):
    """Exception raised by Netapult"""


class DispatchException(NetapultBaseException):
    pass


class UnknownModeException(NetapultBaseException):
    pass


class PromptNotFoundException(NetapultBaseException):
    pass


class UnexpectedValueError(NetapultBaseException):
    pass
