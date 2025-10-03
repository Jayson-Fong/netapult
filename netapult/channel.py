"""
Abstract channel
"""
from abc import abstractmethod
from types import TracebackType


class Channel:
    """
    Abstract channel definition
    """

    def __init__(self, protocol_name: str):
        self.protocol_name: str = protocol_name

    def connect(self):
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError

    @abstractmethod
    def read(self): ...

    @abstractmethod
    def write(self, payload: bytes): ...

    def __enter__(self):
        self.connect()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.disconnect()
