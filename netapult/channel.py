from types import TracebackType


class Channel:
    def __init__(self, protocol_name: str):
        self.protocol_name: str = protocol_name

    def connect(self):
        pass

    def disconnect(self):
        pass

    def read(self, *args, **kwargs):
        pass

    def write(self, payload: bytes, *args, **kwargs):
        pass

    def __enter__(self):
        self.connect()

    def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: TracebackType | None,
    ) -> None:
        self.disconnect()
