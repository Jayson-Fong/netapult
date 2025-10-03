import re
import time
from types import TracebackType
from typing import Literal, overload, Self, Iterable, Any

import netapult.channel


class Client:

    def __init__(
        self,
        channel: netapult.channel.Channel,
        delay_factor: float = 1.0,
        encoding: str = "utf-8",
        errors: str = "backslashreplace",
        return_sequence: str | bytes = b"\n",
        prompt_pattern: str | bytes = rb"(?:\$|#|%|>) ",
        response_return_sequence: str | bytes = b"\n",
        prompt_re_flags: int | re.RegexFlag = 0,
    ):
        self.channel: netapult.channel.Channel = channel
        self.delay_factor: float = delay_factor
        self.encoding: str = encoding
        self.errors: str = errors

        self.return_sequence: bytes = self._encode(return_sequence)
        self.response_return_sequence: bytes = self._encode(response_return_sequence)

        self.prompt_pattern: bytes | None = (
            self._encode(prompt_pattern) if prompt_pattern else None
        )
        self.prompt_re_flags: int | re.RegexFlag = prompt_re_flags

    ############################################################################
    # Channel Connection                                                       #
    ############################################################################

    def connect(self):
        self.channel.connect()

    def disconnect(self):
        self.channel.disconnect()

    ############################################################################
    # Channel Reading                                                          #
    ############################################################################

    @overload
    def read(self, *args, text: Literal[True] = True, **kwargs) -> str: ...

    # fmt: off
    @overload
    def read(
            self, *args, text: Literal[False] = False,
            encoding: str | None = None, errors: str | None = None, **kwargs
    ) -> bytes:
        ...

    # fmt: off
    def read(
            self, *args, text: bool = False,
            encoding: str | None = None, errors: str | None = None, **kwargs
    ) -> str | bytes:
        if text:
            return self._decode(
                self.channel.read(*args, **kwargs),
                encoding=encoding, errors=errors
            )

        return self.channel.read(*args, **kwargs)

    # fmt: off
    @overload
    def read_until_pattern(
            self, pattern: str | bytes, *args,
            re_flags: int | re.RegexFlag = 0, max_buffer_size: int | None = None,
            read_timeout: float | None = None, read_interval: float = 0.1,
            lookback: int = 0, text: Literal[False] = False, **kwargs
    ) -> tuple[bool, bytes]:
        ...

    # fmt: off
    @overload
    def read_until_pattern(
            self, pattern: str | bytes, *args,
            re_flags: int | re.RegexFlag = 0, max_buffer_size: int | None = None,
            read_timeout: float | None = None, read_interval: float = 0.1,
            lookback: int = 0, text: Literal[True] = True,
            encoding: str | None = None, errors: str | None = None, **kwargs
    ) -> tuple[bool, str]:
        ...

    # fmt: off
    def read_until_pattern(
            self, pattern: str | bytes, *args,
            re_flags: int | re.RegexFlag = 0, max_buffer_size: int | None = None,
            read_timeout: float | None = None, read_interval: float = 0.1,
            lookback: int = 0, text: bool = False,
            encoding: str | None = None, errors: str | None = None, **kwargs
    ) -> tuple[bool, bytes | str]:
        if isinstance(pattern, str):
            pattern: bytes = self._encode(pattern, encoding=encoding, errors=errors)

        buffer: bytearray = bytearray()
        pattern: re.Pattern[bytes] = re.compile(pattern, flags=re_flags)
        pattern_found: bool = False

        start_time: float = time.time()
        while ((max_buffer_size is None or len(buffer) < max_buffer_size)
               and (read_timeout is None or time.time() - start_time < read_timeout)):
            buffer += self.channel.read(*args, **kwargs)

            if pattern.search(buffer, len(buffer) - lookback if lookback else 0):
                pattern_found = True
                break

            time.sleep(read_interval * self.delay_factor)

        if text:
            return pattern_found, self._decode(buffer, encoding=encoding, errors=errors)

        return pattern_found, bytes(buffer)

    ############################################################################
    # Channel Writing                                                          #
    ############################################################################

    @overload
    def write(self, content: str, *args, **kwargs) -> None:
        ...

    # fmt: off
    @overload
    def write(
            self, content: bytes, *args,
            encoding: str | None = None, errors: str | None = None, **kwargs
    ) -> None:
        ...

    # fmt: off
    def write(
            self, content: str | bytes, *args,
            encoding: str | None = None, errors: str | None = None, **kwargs
    ) -> None:
        return self.channel.write(
            self._encode(content, encoding=encoding, errors=errors), *args, **kwargs
        )

    ############################################################################
    # Command Execution                                                        #
    ############################################################################

    # noinspection PyUnusedLocal
    def _extract_prompt(
        self, content: bytes, pattern: re.Pattern[bytes], re_flags: int | re.RegexFlag
    ) -> bytes:
        del pattern, re_flags

        return content.strip()

    def find_prompt(
            self, *args, read_delay: float = 1, text: bool = False, prompt_pattern: str | bytes | None = None,
            re_flags: int | re.RegexFlag | None = None,
            encoding: str | None = None, errors: str | None = None,
            return_sequence: str | bytes | None = None, response_return_sequence: str | bytes | None = None,
            write_kwargs: dict[str, Any] | None = None, **kwargs
    ):
        return_sequence, response_return_sequence, prompt_pattern = self._normalize(
            (
                (return_sequence, self.return_sequence),
                (response_return_sequence, self.response_return_sequence),
                (prompt_pattern, self.prompt_pattern),
            ),
            encoding=encoding, errors=errors
        )

        re_flags = self.prompt_re_flags if re_flags is None else re_flags

        # Send a newline to force our terminal into sending a prompt
        self.write(return_sequence, **(write_kwargs or {}))
        time.sleep(read_delay * self.delay_factor)

        # Given a pattern, read until it to locate our prompt content
        pattern_found, content = self.read_until_pattern(
            *args, pattern=prompt_pattern, re_flags=re_flags, **kwargs
        )

        if not pattern_found:
            return False, None

        content: bytes
        end_index: int = len(content)

        prompt_search_pattern: re.Pattern[bytes] = re.compile(prompt_pattern, flags=re_flags)

        while end_index > 0:
            # Find our first line of usable content starting from the end
            newline_index: int = content.rfind(response_return_sequence, 0, end_index)
            if newline_index == -1:
                return False, None

            match: re.Match[bytes] | None = prompt_search_pattern.search(content[newline_index:])
            if match:
                prompt: bytes = self._extract_prompt(
                    content[newline_index:end_index],
                    pattern=prompt_search_pattern,
                    re_flags=re_flags,
                )

                if text:
                    return True, self._decode(prompt, encoding=encoding, errors=errors)

                return True, prompt

            end_index = newline_index

        return None

    ############################################################################
    # Utilities                                                                #
    ############################################################################

    def _encode(self, data: str | bytes, encoding: str | None = None, errors: str | None = None) -> bytes:
        if isinstance(data, bytes):
            return data

        return data.encode(
            encoding=encoding or self.encoding,
            errors=errors or self.errors,
        )

    def _decode(self, data: str | bytes, encoding: str | None = None, errors: str | None = None) -> str:
        if isinstance(data, str):
            return data

        return data.decode(
            encoding=encoding or self.encoding,
            errors=errors or self.errors,
        )

    def _normalize(
            self, proposed: str | bytes | Iterable[tuple[str | bytes | None, str | bytes | None]] | None,
            fallback: str | bytes | None = None,
            encoding: str | None = None, errors: str | None = None
    ) -> bytes | tuple[bytes | None, ...] | None:
        if isinstance(proposed, Iterable) and not isinstance(proposed, (str, bytes)):
            normalized_entries: list[bytes | None] = []
            for entry in proposed:
                normalized_entries.append(self._normalize(*entry, encoding=encoding, errors=errors))

            return tuple(normalized_entries)

        if proposed is None:
            return fallback

        return self._encode(proposed, encoding=encoding, errors=errors)

    ############################################################################
    # Context Manager                                                          #
    ############################################################################

    def __enter__(self) -> Self:
        self.connect()
        return self

    def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: TracebackType | None,
    ) -> None:
        self.disconnect()
