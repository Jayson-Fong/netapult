"""
Client

Provides the `Client` class used for interacting with a device.
"""

import logging
import re
import time
from contextlib import contextmanager
from types import TracebackType
from typing import Self, Any, overload, Generator

from . import channel as _channel
from . import exceptions as _exceptions
from . import util as _util
from .constants import DEFAULT, DEFAULT_TYPE
from . import _decorators as decorators

logger: logging.Logger = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
class Client:
    """
    Interface for interacting with a device.
    """

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

    def initialize(self) -> None:
        """
        Initializes the connection.
        """

    def connect(self) -> None:
        """
        Attempts to connect and initialize the connection.
        """

        self.channel.connect()
        self.initialize()

    def cleanup(self) -> None:
        """
        Cleans up the channel in preparation to disconnect.
        """

    def disconnect(self) -> None:
        """
        Attempt to gracefully disconnect.
        """

        # noinspection PyBroadException
        # pylint: disable=broad-exception-caught
        try:
            self.cleanup()
        except Exception:
            logger.exception("Encountered cleanup exception")

        # noinspection PyBroadException
        # pylint: disable=broad-exception-caught
        try:
            self.channel.disconnect()
        except Exception:
            logger.exception("Encountered disconnect exception")

    ############################################################################
    # Channel Reading                                                          #
    ############################################################################

    @overload
    @decorators.decode
    def read(self, *args, text: True, **kwargs) -> str: ...

    @overload
    @decorators.decode
    def read(self, *args, text: False, **kwargs) -> bytes: ...

    # noinspection PyUnusedLocal
    @decorators.decode
    def read(self, *args, **kwargs) -> bytes:
        """
        Reads data from the channel.

        :param args: Arguments to pass to the channel read.
        :param kwargs: Keyword arguments to pass to the channel read.
        :return: Data read from the channel.
        """

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
        text: False,
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
        """
        Reads data from the channel until the pattern is found.

        :param pattern: Pattern to match against.
        :param args: Arguments to pass to `read`.
        :param re_flags: Regular expression flags to use when matching with the pattern.
        :param max_buffer_size: Maximum buffer size, loosely enforced.
        :param read_timeout: Maximum number of seconds to read before timing out.
        :param read_interval: Number of seconds to wait between reads.
        :param lookback: Number of bytes from the end to match the pattern against.
        :param kwargs: Keyword arguments to pass to `read`.
        :return:
        """

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
    def write(self, content: str, **kwargs) -> Any: ...

    @decorators.encode
    def write(self, content: bytes, **kwargs) -> Any:
        """
        Writes data to the channel.

        :param content: Payload to write to the channel.
        :param kwargs: Keyword arguments to pass to the channel write function.
        """

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
        text: False,
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
        """
        Attempts to identify the prompt for a device.

        Sends the return sequence then attempts to find
        a line matching the specified `prompt_pattern`.

        :param args: Arguments to pass to `read_until_pattern`.
        :param read_delay: Seconds after writing the return sequence to wait before continuing.
        :param prompt_pattern: Pattern to find the prompt.
        :param re_flags: Regular expression flags to use when matching with the pattern.
        :param return_sequence: Payload to send to cause a re-print of the prompt.
        :param response_return_sequence: Characters to identify line feeds.
        :param write_kwargs: Keyword arguments to pass to `write`.
        :param kwargs: Keyword arguments to pass to `read_until_pattern`.
        :return: Prompt if found, None otherwise.
        """

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
        command: str | bytes,
        text: False,
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
        """
        Sends a command and reads until the prompt is detected.

        :param command: Command to send.
        :param prompt: Prompt to identify the end of output.
        :param return_sequence: Sequence of characters to indicate the end of the command.
        :param normalize_command: Whether to normalize the command.
        :param find_prompt_kwargs: Keyword arguments to pass to `find_prompt`.
        :param write_kwargs: Keyword arguments to pass to `write`.
        :param kwargs: Keyword arguments to pass to `read_until_pattern`.
        :return: Tuple of whether the prompt was found and the output.
        """

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
    def enter_mode(self, name: str, *args, **kwargs) -> Any:
        """
        Enters the `name` mode.

        :param name: Name of the mode to enter.
        :param args: Arguments to establish the mode.
        :param kwargs: Keyword arguments to establish the mode.
        :return: Unspecified - depends on the mode.
        """

        del args, kwargs
        raise _exceptions.UnknownModeException(f"Unknown mode: {name}")

    # noinspection PyUnusedLocal
    def exit_mode(self, name: str, *args, **kwargs) -> Any:
        """
        Exits the `name` mode.

        :param name: Name of the mode to exit.
        :param args: Arguments used to establish the mode.
        :param kwargs: Keyword arguments used to establish the mode.
        :return: Unspecified - depends on the mode.
        """

        del args, kwargs
        raise _exceptions.UnknownModeException(f"Unknown mode: {name}")

    @contextmanager
    def mode(self, name: str, *args, **kwargs) -> Generator["Client", Any, None]:
        """
        Context manager for entering a mode.

        Used to enable mode switching such as privilege escalation.

        :param name: Name of the mode to switch into.
        :param args: Arguments to establish the mode.
        :param kwargs: Keyword arguments to establish the mode.
        :yields: Self
        """

        self.enter_mode(name, *args, **kwargs)
        try:
            yield self
        finally:
            self.exit_mode(name, *args, **kwargs)

    ############################################################################
    # Context Manager                                                          #
    ############################################################################

    def __enter__(self) -> Self:
        """
        Attempts to connect the client.

        :return: Self
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
        Attempts to gracefully disconnect the client.

        :param exc_type: Exception type, if applicable.
        :param exc_val: Exception, if applicable.
        :param exc_tb: Exception traceback, if applicable.
        """

        # noinspection PyBroadException
        # pylint: disable=broad-exception-caught
        try:
            self.disconnect()
        except Exception:
            logger.exception("Failed to gracefully disconnect.")


__all__: tuple[str, ...] = ("Client",)
