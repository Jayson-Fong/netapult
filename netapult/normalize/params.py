import inspect
from functools import wraps
from typing import TYPE_CHECKING, Callable, TypeVar, ParamSpec, Any

import netapult.netapult_globals


if TYPE_CHECKING:

    from ._types import EncodingSpecified


P = ParamSpec("P")
R = TypeVar("R")


def encode(func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(self: "EncodingSpecified", *args: P.args, **kwargs: P.kwargs) -> R:
        def _encode(value: Any) -> Any:
            if isinstance(value, str):
                return value.encode(self.encoding, self.errors)

            return value

        args = tuple(_encode(entry) for entry in args)

        for key, value in kwargs.items():
            if isinstance(value, str):
                kwargs[key] = value.encode(self.encoding, self.errors)

        return func(self, *args, **kwargs)

    return wrapper


def encode_argument(*encode_args: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        def wrapper(self: object, *args, **kwargs):
            sig: inspect.Signature = inspect.signature(func)
            bound: inspect.BoundArguments = sig.bind(self, *args, **kwargs)
            bound.apply_defaults()

            encoding: str = bound.arguments["encoding"]
            errors: str = bound.arguments["errors"]

            for argument_name in encode_args:
                value: Any = bound.arguments[argument_name]
                if isinstance(value, str):
                    value = value.encode(encoding, errors)

                bound.arguments[argument_name] = value

            return func(*bound.args, **bound.kwargs)

        return wrapper

    return decorator


def default(**normalization_kwargs: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        def wrapper(self: object, *args, **kwargs):
            sig: inspect.Signature = inspect.signature(func)
            bound: inspect.BoundArguments = sig.bind(self, *args, **kwargs)
            bound.apply_defaults()

            for argument_name, default_name in normalization_kwargs.items():
                if bound.arguments[argument_name] is netapult.netapult_globals.DEFAULT:
                    bound.arguments[argument_name] = getattr(self, default_name)

            return func(*bound.args, **bound.kwargs)

        return wrapper

    return decorator


__all__: tuple[str, ...] = ("encode", "default")
