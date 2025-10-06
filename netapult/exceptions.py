"""
Exceptions raised within the package
"""

import abc


class NetapultBaseException(Exception, abc.ABC):
    """Exception raised by Netapult"""


class DispatchException(NetapultBaseException):
    """Error while dispatching"""


class UnknownModeException(NetapultBaseException):
    """Requested mode is unknown"""


class PromptNotFoundException(NetapultBaseException):
    """Failed to find prompt"""


__all__: tuple[str, ...] = (
    "NetapultBaseException",
    "DispatchException",
    "UnknownModeException",
    "PromptNotFoundException",
)
