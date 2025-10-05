import functools
import importlib
import inspect
import re
from typing import Any, TypeVar, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    import netapult.client

NAME_PATTERN: re.Pattern[str] = re.compile(
    r"(?P<module>[\w.]+)\s*(:\s*(?P<attr>[\w.]+)\s*)?((?P<extras>\[.*])\s*)?$"
)


def load_named_object(name: str) -> Any:
    match = NAME_PATTERN.match(name)
    module = importlib.import_module(match.group("module"))
    attrs = filter(None, (match.group("attr") or "").split("."))
    return functools.reduce(getattr, attrs, module)


# pylint: disable=too-many-arguments,too-many-positional-arguments
def apply_normalization(
    bound: inspect.BoundArguments,
    keyword: str,
    obj: Any,
    fallback_variable: str | None = None,
    encoding: str = "utf-8",
    errors: str = "backslashreplace",
):
    proposed = bound.arguments.get(keyword)
    if isinstance(proposed, str):
        proposed = proposed.encode(encoding, errors)

    if proposed is None and fallback_variable is not None:
        proposed = getattr(obj, fallback_variable)

    bound.arguments[keyword] = proposed


F = TypeVar("F", bound=Callable[..., Any])


def normalize(*normalization_args: str | int, **normalization_kwargs):
    def decorator(func: F):
        def wrapper(self: "netapult.client.Client", *args, **kwargs):
            sig = inspect.signature(func)
            bound = sig.bind(self, *args, **kwargs)
            bound.apply_defaults()

            # Determine the encoding to use
            encoding: str = bound.arguments.get("encoding") or self.encoding
            errors: str = bound.arguments.get("errors") or self.errors

            normalize_index: int | None = None
            for keyword in normalization_args:
                if isinstance(keyword, int):
                    normalize_index = keyword
                    continue

                apply_normalization(bound, keyword, self, None, encoding, errors)

            for keyword, fallback_variable in normalization_kwargs.items():
                apply_normalization(
                    bound, keyword, self, fallback_variable, encoding, errors
                )

            result = func(*bound.args, **bound.kwargs)
            if normalize_index is None or not bound.arguments.get("text"):
                return result

            if isinstance(result, tuple):
                if not isinstance(result[normalize_index], bytes):
                    return result

                result = list(result)
                result[normalize_index] = result[normalize_index].decode(
                    encoding, errors
                )
                return tuple(result)

            if isinstance(result, bytes):
                return result.decode(encoding, errors)

            return result

        return wrapper

    return decorator


STRIP_ANSI_PATTERN: re.Pattern[bytes] = re.compile(rb"\x1B\[[0-?]*[ -/]*[@-~]")


def strip_ansi(data: bytes) -> bytes:
    return STRIP_ANSI_PATTERN.sub(b"", data)


def rfind_multi_char(
    content: str | bytes,
    target: tuple[str | bytes, ...],
    start: int = 0,
    end: int | None = None,
) -> int:
    if end is None:
        end: int = len(content)

    for i in range(end - 1, start - 1, -1):
        if content[i] in target:
            return i

    return -1


__all__: tuple[str, ...] = ("load_named_object", "normalize", "strip_ansi")
