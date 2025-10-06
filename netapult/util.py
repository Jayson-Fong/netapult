"""
General utilities
"""

import functools
import importlib
import re
from typing import Any

NAME_PATTERN: re.Pattern[str] = re.compile(
    r"(?P<module>[\w.]+)\s*(:\s*(?P<attr>[\w.]+)\s*)?((?P<extras>\[.*])\s*)?$"
)


def load_object(name: str) -> Any:
    """
    Loads an object given an entry point specification.

    Entry point specifications consist of a module path,
    attribute, and an optional extra. For example:
    package.module:ClassName.

    :param name: Entry point specification.
    :return: Requested object.
    """

    match = NAME_PATTERN.match(name)
    module = importlib.import_module(match.group("module"))
    attrs = filter(None, (match.group("attr") or "").split("."))
    return functools.reduce(getattr, attrs, module)


STRIP_ANSI_PATTERN: re.Pattern[bytes] = re.compile(rb"\x1B\[[0-?]*[ -/]*[@-~]")


def strip_ansi(data: bytes) -> bytes:
    """
    Strips ANSI escape codes from the input.

    :param data: Data to sanitize.
    :return: Sanitized data.
    """
    return STRIP_ANSI_PATTERN.sub(b"", data)


def rfind_any(
    content: str | bytes,
    target: tuple[str | int, ...],
    start: int = 0,
    end: int | None = None,
) -> int:
    """
    Starting from the end, looks for the first instance of a targeted character.

    :param content: The content to search through.
    :param target: A tuple of either targeted strings or integers (used for searching bytes).
    :param start: Minimum index to search.
    :param end: Maximum index to search.
    :return: Last occurrence index of targets in the specified range, or -1 if not found.
    """

    if end is None:
        end: int = len(content)

    for i in range(end - 1, start - 1, -1):
        if content[i] in target:
            return i

    return -1


__all__: tuple[str, ...] = ("load_object", "strip_ansi", "rfind_any")
