from types import TracebackType


class Channel:
    def __init__(self, protocol_name: str):
        self.protocol_name: str = protocol_name

    def connect(self):
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError

    def read(self):
        raise NotImplementedError

    def write(self, payload: bytes):
        raise NotImplementedError

    def __enter__(self):
        self.connect()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.disconnect()
