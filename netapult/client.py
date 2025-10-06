import logging
import re
import time
from contextlib import contextmanager
from types import TracebackType
from typing import Self, Any, overload

from . import channel as _channel
from . import exceptions as _exceptions
from . import util as _util
from .constants import DEFAULT, DEFAULT_TYPE
from . import _decorators as decorators

logger: logging.Logger = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
class Client:

    # pylint: disable=too-many-positional-arguments,too-many-arguments
    @decorators.encode_argument(
        "prompt_pattern", "prompt", "return_sequence", "response_return_sequence"
    )
    @overload
    def __init__(
        self,
        channel: _channel.Channel,
        delay_factor: float = 1.0,
        encoding: str = "utf-8",
        errors: str = "backslashreplace",
        return_sequence: str | bytes = b"\n",
        prompt: str | bytes | None = None,
        prompt_pattern: str | bytes = rb"(?:\$|#|%|>) ",
        response_return_sequence: str | bytes = b"\n\r",
        prompt_re_flags: int | re.RegexFlag = 0,
        normalize_commands: bool = True,
        **kwargs,
    ): ...

    # pylint: disable=too-many-positional-arguments,too-many-arguments
    @decorators.encode_argument(
        "prompt_pattern", "prompt", "return_sequence", "response_return_sequence"
    )
    def __init__(
        self,
        channel: _channel.Channel,
        delay_factor: float = 1.0,
        encoding: str = "utf-8",
        errors: str = "backslashreplace",
        return_sequence: bytes = b"\n",
        prompt: bytes | None = None,
        prompt_pattern: bytes = rb"(?:\$|#|%|>) ",
        response_return_sequence: bytes = b"\n\r",
        prompt_re_flags: int | re.RegexFlag = 0,
        normalize_commands: bool = True,
        **kwargs,
    ):
        """
        Initializes the client.

        :param channel: Channel to read and write data to/from.
        :param delay_factor: Factor to multiply delay times by.
        :param encoding: Encoding to use.
        :param errors: Encoding error resolution strategy.
        :param return_sequence: Sequence of characters to use as return.
        :param prompt: System prompt.
        :param prompt_pattern: Regular expression to match the prompt.
        :param response_return_sequence: Sequence of characters to identify line breaks.
        :param prompt_re_flags: Regular expression flags to match the prompt.
        :param normalize_commands: Whether to normalize commands before executing.
        :param kwargs: Unused - provided to prevent errors.
        """

        # kwargs is accepted here to generically accept certain keyword
        # arguments such as privilege passwords, which may not be
        # available universally, but our user may want to assume it is.
        for kwarg_key in kwargs:
            logger.warning(
                "Received unexpected keyword initialization argument: %s", kwarg_key
            )

        self.channel: _channel.Channel = channel
        self.protocol: str = channel.protocol_name
        self.delay_factor: float = delay_factor
        self.encoding: str = encoding
        self.errors: str = errors
        self.normalize_commands = normalize_commands

        self.return_sequence: bytes = return_sequence
        self.response_return_sequence: bytes = response_return_sequence

        self.prompt: bytes | None = prompt
        self.prompt_pattern: bytes | None = prompt_pattern
        self.prompt_re_flags: int | re.RegexFlag = prompt_re_flags

    ############################################################################
    # Channel Connection                                                       #
    ############################################################################

    def initialize(self):
        pass

    def connect(self):
        self.channel.connect()
        self.initialize()

    def cleanup(self):
        pass

    def disconnect(self):
        # noinspection PyBroadException
        # pylint: disable=broad-exception-caught
        try:
            self.cleanup()
        except Exception:
            logger.exception("Encountered cleanup exception")

        self.channel.disconnect()

    ############################################################################
    # Channel Reading                                                          #
    ############################################################################

    @overload
    @decorators.decode
    def read(self, *args, text: True, **kwargs) -> str:
        # noinspection PyArgumentList
        return self.channel.read(*args, **kwargs)

    # noinspection PyUnusedLocal
    @decorators.decode
    def read(self, *args, **kwargs) -> bytes:
        # noinspection PyArgumentList
        return self.channel.read(*args, **kwargs)

    @decorators.decode
    @decorators.encode
    @overload
    def read_until_pattern(
        self,
        pattern: str | bytes,
        *args,
        text: True,
        re_flags: int | re.RegexFlag = 0,
        max_buffer_size: int | None = None,
        read_timeout: float | None = None,
        read_interval: float = 0.1,
        lookback: int = 0,
        **kwargs,
    ) -> tuple[bool, str]: ...

    @decorators.decode
    @decorators.encode
    @overload
    def read_until_pattern(
        self,
        pattern: str,
        *args,
        text: True,
        re_flags: int | re.RegexFlag = 0,
        max_buffer_size: int | None = None,
        read_timeout: float | None = None,
        read_interval: float = 0.1,
        lookback: int = 0,
        **kwargs,
    ) -> tuple[bool, bytes]: ...

    # noinspection PyUnusedLocal
    @decorators.decode
    @decorators.encode
    def read_until_pattern(
        self,
        pattern: bytes,
        *args,
        re_flags: int | re.RegexFlag = 0,
        max_buffer_size: int | None = None,
        read_timeout: float | None = None,
        read_interval: float = 0.1,
        lookback: int = 0,
        **kwargs,
    ) -> tuple[bool, bytes]:
        logger.info("Searching for pattern: %s", pattern)

        buffer: bytearray = bytearray()
        pattern: re.Pattern[bytes] = re.compile(pattern, flags=re_flags)
        pattern_found: bool = False

        start_time: float = time.time()
        while (max_buffer_size is None or len(buffer) < max_buffer_size) and (
            read_timeout is None or time.time() - start_time < read_timeout
        ):
            # noinspection PyArgumentList
            buffer += self.channel.read(*args, **kwargs)

            if pattern.search(buffer, len(buffer) - lookback if lookback else 0):
                pattern_found = True
                break

            time.sleep(read_interval * self.delay_factor)

        return pattern_found, bytes(buffer)

    ############################################################################
    # Channel Writing                                                          #
    ############################################################################

    @decorators.encode
    @overload
    def write(self, content: str, **kwargs) -> None: ...

    @decorators.encode
    def write(self, content: bytes, **kwargs) -> None:
        # noinspection PyArgumentList
        return self.channel.write(content, **kwargs)

    ############################################################################
    # Command Execution                                                        #
    ############################################################################

    # noinspection PyUnusedLocal
    def _extract_prompt(
        self, content: bytes, pattern: re.Pattern[bytes], re_flags: int | re.RegexFlag
    ) -> bytes:
        del pattern, re_flags

        return _util.strip_ansi(content).strip()

    @decorators.decode
    @decorators.default(
        return_sequence="return_sequence",
        response_return_sequence="response_return_sequence",
        prompt_pattern="prompt_pattern",
    )
    @overload
    def find_prompt(
        self,
        *args,
        text: True,
        read_delay: float = 1,
        prompt_pattern: bytes | DEFAULT_TYPE = DEFAULT,
        re_flags: int | re.RegexFlag | None = None,
        return_sequence: bytes | DEFAULT_TYPE = DEFAULT,
        response_return_sequence: bytes | DEFAULT_TYPE = DEFAULT,
        write_kwargs: dict[str, Any] | None = None,
        **kwargs,
    ) -> str | None: ...

    # noinspection PyUnusedLocal
    # pylint: disable=too-many-locals,too-many-arguments
    @decorators.decode
    @decorators.default(
        return_sequence="return_sequence",
        response_return_sequence="response_return_sequence",
        prompt_pattern="prompt_pattern",
    )
    def find_prompt(
        self,
        *args,
        read_delay: float = 1,
        prompt_pattern: bytes | DEFAULT_TYPE = DEFAULT,
        re_flags: int | re.RegexFlag | None = None,
        return_sequence: bytes | DEFAULT_TYPE = DEFAULT,
        response_return_sequence: bytes | DEFAULT_TYPE = DEFAULT,
        write_kwargs: dict[str, Any] | None = None,
        **kwargs,
    ) -> bytes | None:
        re_flags = self.prompt_re_flags if re_flags is None else re_flags

        # Send a newline to force our terminal into sending a prompt
        self.write(return_sequence, **(write_kwargs or {}))
        time.sleep(read_delay * self.delay_factor)

        # Given a pattern, read until it to locate our prompt content
        pattern_found, content = self.read_until_pattern(
            *args, pattern=prompt_pattern, re_flags=re_flags, **kwargs
        )

        if not pattern_found:
            return None

        content: bytes
        end_index: int = len(content)

        prompt_search_pattern: re.Pattern[bytes] = re.compile(
            prompt_pattern, flags=re_flags
        )

        while end_index > 0:
            # Find our first line of usable content starting from the end
            newline_index: int = _util.rfind_any(
                content, tuple(response_return_sequence), 0, end_index
            )
            if newline_index == -1:
                return None

            match: re.Match[bytes] | None = prompt_search_pattern.search(
                content[newline_index:]
            )
            if match:
                prompt: bytes = self._extract_prompt(
                    content[newline_index:end_index],
                    pattern=prompt_search_pattern,
                    re_flags=re_flags,
                )

                return prompt

            end_index = newline_index

        return None

    @decorators.encode
    @decorators.default(return_sequence="return_sequence")
    def _normalize_command(
        self,
        command: bytes,
        return_sequence: bytes | DEFAULT_TYPE = DEFAULT,
    ) -> bytes:
        command: bytes

        if not command.endswith(return_sequence):
            command = command + return_sequence

        return command

    @decorators.decode
    @decorators.encode
    @decorators.default(
        prompt="prompt",
        normalize_command="normalize_commands",
        return_sequence="return_sequence",
    )
    @overload
    def run_command(
        self,
        command: str | bytes,
        text: True,
        prompt: bytes | DEFAULT_TYPE = DEFAULT,
        return_sequence: bytes | DEFAULT_TYPE = DEFAULT,
        normalize_command: bool | DEFAULT_TYPE = DEFAULT,
        find_prompt_kwargs: dict[str, Any] | None = None,
        write_kwargs: dict[str, Any] | None = None,
        **kwargs,
    ) -> tuple[bool, str]: ...

    @decorators.decode
    @decorators.encode
    @decorators.default(
        prompt="prompt",
        normalize_command="normalize_commands",
        return_sequence="return_sequence",
    )
    @overload
    def run_command(
        self,
        command: str,
        prompt: bytes | DEFAULT_TYPE = DEFAULT,
        return_sequence: bytes | DEFAULT_TYPE = DEFAULT,
        normalize_command: bool | DEFAULT_TYPE = DEFAULT,
        find_prompt_kwargs: dict[str, Any] | None = None,
        write_kwargs: dict[str, Any] | None = None,
        **kwargs,
    ) -> tuple[bool, bytes]: ...

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    @decorators.decode
    @decorators.encode
    @decorators.default(
        prompt="prompt",
        normalize_command="normalize_commands",
        return_sequence="return_sequence",
    )
    def run_command(
        self,
        command: bytes,
        prompt: bytes | DEFAULT_TYPE = DEFAULT,
        return_sequence: bytes | DEFAULT_TYPE = DEFAULT,
        normalize_command: bool | DEFAULT_TYPE = DEFAULT,
        find_prompt_kwargs: dict[str, Any] | None = None,
        write_kwargs: dict[str, Any] | None = None,
        **kwargs,
    ) -> tuple[bool, bytes]:
        if not prompt:
            prompt = self.find_prompt(**(find_prompt_kwargs or {}))
            if prompt is None:
                raise _exceptions.PromptNotFoundException("Failed to find prompt")

        if normalize_command:
            command: bytes = self._normalize_command(command, return_sequence)

        self.write(command, **(write_kwargs or {}))

        # noinspection PyTypeChecker
        normalized_prompt: bytes = re.escape(prompt)
        return self.read_until_pattern(normalized_prompt, **kwargs)

    ############################################################################
    # Terminal State Management                                                #
    ############################################################################

    # noinspection PyUnusedLocal
    def enter_mode(self, name: str, *args, **kwargs):
        del args, kwargs
        raise _exceptions.UnknownModeException(f"Unknown mode: {name}")

    # noinspection PyUnusedLocal
    def exit_mode(self, name: str, *args, **kwargs):
        del args, kwargs
        raise _exceptions.UnknownModeException(f"Unknown mode: {name}")

    @contextmanager
    def mode(self, name: str, *args, **kwargs):
        self.enter_mode(name, *args, **kwargs)
        yield self
        self.exit_mode(name, *args, **kwargs)

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


__all__: tuple[str, ...] = ("Client",)
