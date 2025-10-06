"""
Abstract channel
"""

import logging
from abc import abstractmethod
from types import TracebackType
from typing import Any, Self


logger = logging.getLogger(__name__)


class Channel:
    """
    Abstract communication channel interface.
    """

    def __init__(self, protocol_name: str):
        self.protocol_name: str = protocol_name

    def connect(self) -> None:
        """
        Attempts to connect to the device.
        """

        raise NotImplementedError

    def disconnect(self) -> None:
        """
        Attempt to gracefully disconnect from the device.
        """

        raise NotImplementedError

    @abstractmethod
    def read(self) -> bytes:
        """
        Reads data from the channel.

        :return: The read data.
        """

    @abstractmethod
    def write(self, payload: bytes) -> Any:
        """
        Writes the full payload to the channel.

        :param payload: Payload to write.
        :return: Unspecified - up to protocol discretion.
        """

    def __enter__(self) -> Self:
        """
        Attempt to establish a connection.

        :return: The channel.
        """

        self.connect()
        return self

    # pylint: disable=duplicate-code
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """
        Attempt to gracefully disconnect.

        :param exc_type: Exception type, if applicable.
        :param exc_val: Exception, if applicable.
        :param exc_tb: Traceback, if applicable.
        """

        # noinspection PyBroadException
        # pylint: disable=broad-exception-caught
        try:
            self.disconnect()
        except Exception:
            logger.exception("Failed to gracefully disconnect.")


__all__: tuple[str, ...] = ("Channel",)
