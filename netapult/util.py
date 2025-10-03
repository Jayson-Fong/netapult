import functools
import importlib
import re


NAME_PATTERN: re.Pattern[str] = re.compile(
    r"(?P<module>[\w.]+)\s*" r"(:\s*(?P<attr>[\w.]+)\s*)?" r"((?P<extras>\[.*\])\s*)?$"
)


def load_named_object(name: str):
    match = NAME_PATTERN.match(name)
    module = importlib.import_module(match.group("module"))
    attrs = filter(None, (match.group("attr") or "").split("."))
    return functools.reduce(getattr, attrs, module)


__all__: tuple[str, ...] = ("load_named_object",)
