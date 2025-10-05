import logging
import re
import time
from contextlib import contextmanager
from types import TracebackType
from typing import overload, Self, Any

import netapult.channel
import netapult.exceptions
from netapult.util import normalize

logger: logging.Logger = logging.getLogger(__name__)


class Client:

    @normalize(
        "prompt_pattern", "prompt", "return_sequence", "response_return_sequence"
    )
    def __init__(
        self,
        channel: netapult.channel.Channel,
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
    ):
        # kwargs is accepted here to generically accept certain keyword
        # arguments such as privilege passwords, which may not be
        # available universally, but our user may want to assume it is.
        for kwarg_key in kwargs:
            logger.warning(
                "Received unexpected keyword initialization argument: %s", kwarg_key
            )

        self.channel: netapult.channel.Channel = channel
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
        try:
            self.cleanup()
        except:
            logger.exception("Encountered cleanup exception")

        self.channel.disconnect()

    ############################################################################
    # Channel Reading                                                          #
    ############################################################################

    @overload
    def read(self, *args, text: True = True, **kwargs) -> str: ...

    @overload
    def read(
        self,
        *args,
        text: False = False,
        encoding: str | None = None,
        errors: str | None = None,
        **kwargs,
    ) -> bytes: ...

    # noinspection PyUnusedLocal
    @normalize(0)
    def read(
        self,
        *args,
        text: bool = False,
        encoding: str | None = None,
        errors: str | None = None,
        **kwargs,
    ) -> str | bytes:
        del text, encoding, errors

        # noinspection PyArgumentList
        return self.channel.read(*args, **kwargs)

    @overload
    def read_until_pattern(
        self,
        pattern: str | bytes,
        *args,
        re_flags: int | re.RegexFlag = 0,
        max_buffer_size: int | None = None,
        read_timeout: float | None = None,
        read_interval: float = 0.1,
        lookback: int = 0,
        text: False = False,
        **kwargs,
    ) -> tuple[bool, bytes]: ...

    @overload
    def read_until_pattern(
        self,
        pattern: str | bytes,
        *args,
        re_flags: int | re.RegexFlag = 0,
        max_buffer_size: int | None = None,
        read_timeout: float | None = None,
        read_interval: float = 0.1,
        lookback: int = 0,
        text: True = True,
        encoding: str | None = None,
        errors: str | None = None,
        **kwargs,
    ) -> tuple[bool, str]: ...

    # noinspection PyUnusedLocal
    @normalize(1, "pattern")
    def read_until_pattern(
        self,
        pattern: str | bytes,
        *args,
        re_flags: int | re.RegexFlag = 0,
        max_buffer_size: int | None = None,
        read_timeout: float | None = None,
        read_interval: float = 0.1,
        lookback: int = 0,
        text: bool = False,
        encoding: str | None = None,
        errors: str | None = None,
        **kwargs,
    ) -> tuple[bool, bytes | str]:
        del text, encoding, errors

        pattern: bytes

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

    @overload
    def write(self, content: str, **kwargs) -> None: ...

    @overload
    def write(
        self,
        content: bytes,
        encoding: str | None = None,
        errors: str | None = None,
        **kwargs,
    ) -> None: ...

    # noinspection PyUnusedLocal
    @normalize("content")
    def write(
        self,
        content: str | bytes,
        encoding: str | None = None,
        errors: str | None = None,
        **kwargs,
    ) -> None:
        del encoding, errors

        content: bytes
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

        return netapult.util.strip_ansi(content).strip()

    # noinspection PyUnusedLocal
    @normalize(
        1,
        return_sequence="return_sequence",
        response_return_sequence="response_return_sequence",
        prompt_pattern="prompt_pattern",
    )
    def find_prompt(
        self,
        *args,
        read_delay: float = 1,
        text: bool = False,
        prompt_pattern: str | bytes | None = None,
        re_flags: int | re.RegexFlag | None = None,
        encoding: str | None = None,
        errors: str | None = None,
        return_sequence: str | bytes | None = None,
        response_return_sequence: str | bytes | None = None,
        write_kwargs: dict[str, Any] | None = None,
        **kwargs,
    ):
        del text, encoding, errors
        prompt_pattern: bytes | None

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

        prompt_search_pattern: re.Pattern[bytes] = re.compile(
            prompt_pattern, flags=re_flags
        )

        while end_index > 0:
            # Find our first line of usable content starting from the end
            newline_index: int = netapult.util.rfind_multi_char(
                content, tuple(response_return_sequence), 0, end_index
            )
            if newline_index == -1:
                return False, None

            match: re.Match[bytes] | None = prompt_search_pattern.search(
                content[newline_index:]
            )
            if match:
                prompt: bytes = self._extract_prompt(
                    content[newline_index:end_index],
                    pattern=prompt_search_pattern,
                    re_flags=re_flags,
                )

                return True, prompt

            end_index = newline_index

        return False, None

    # noinspection PyUnusedLocal
    @normalize("command", return_sequence="return_sequence")
    def _normalize_command(
        self,
        command: str | bytes,
        return_sequence: str | bytes | None = None,
        encoding: str | None = None,
        errors: str | None = None,
    ) -> bytes:
        del encoding, errors
        command: bytes

        if not command.endswith(return_sequence):
            command = command + return_sequence

        return command

    @normalize(0, prompt="prompt", normalize_command="normalize_commands")
    def run_command(
        self,
        command: str | bytes,
        prompt: str | bytes | None = None,
        return_sequence: str | bytes | None = None,
        normalize_command: bool | None = None,
        find_prompt_kwargs: dict[str, Any] | None = None,
        write_kwargs: dict[str, Any] | None = None,
        **kwargs,
    ) -> tuple[bool, str | bytes]:
        if not prompt:
            prompt_found, prompt = self.find_prompt(**(find_prompt_kwargs or {}))
            if not prompt_found:
                raise netapult.exceptions.PromptNotFoundException(
                    "Failed to find prompt"
                )

        if normalize_command:
            command: bytes = self._normalize_command(
                command,
                return_sequence,
                encoding=kwargs.get("encoding"),
                errors=kwargs.get("errors"),
            )

        self.write(command, **(write_kwargs or {}))
        return self.read_until_pattern(re.escape(prompt), **kwargs)

    ############################################################################
    # Terminal State Management                                                #
    ############################################################################

    # noinspection PyUnusedLocal
    def enter_mode(self, name: str, *args, **kwargs):
        del args, kwargs
        raise netapult.exceptions.UnknownModeException(f"Unknown mode: {name}")

    # noinspection PyUnusedLocal
    def exit_mode(self, name: str, *args, **kwargs):
        del args, kwargs
        raise netapult.exceptions.UnknownModeException(f"Unknown mode: {name}")

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
