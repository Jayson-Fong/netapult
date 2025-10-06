import inspect
from functools import wraps
from typing import Protocol, TYPE_CHECKING, Callable, TypeVar, ParamSpec, Any

from .constants import DEFAULT

P = ParamSpec("P")
R = TypeVar("R")


if TYPE_CHECKING:
    # pylint: disable=too-few-public-methods
    class EncodingSpecified(Protocol):
        encoding: str
        errors: str

    # pylint: disable=too-few-public-methods
    class DecodeNormalizer(Protocol[P, R]):

        def __call__(
            self: "EncodingSpecified",
            *args: P.args,
            text: bool = False,
            **kwargs: P.kwargs,
        ) -> R: ...


def decode(func: Callable[P, R]) -> Callable[P, R] | "DecodeNormalizer[P, R]":
    @wraps(func)
    def wrapper(
        self: "EncodingSpecified", *args: P.args, text: bool = False, **kwargs: P.kwargs
    ) -> R:
        result = func(self, *args, **kwargs)

        if not text:
            return result

        if isinstance(result, (bytes, bytearray)):
            return result.decode(self.encoding, self.errors)

        if isinstance(result, tuple):

            def _decode(value):
                if isinstance(value, (bytes, bytearray)):
                    return value.decode(self.encoding, self.errors)

                return value

            return tuple(_decode(entry) for entry in result)

        return result

    return wrapper


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
                if bound.arguments[argument_name] is DEFAULT:
                    bound.arguments[argument_name] = getattr(self, default_name)

            return func(*bound.args, **bound.kwargs)

        return wrapper

    return decorator


__all__: tuple[str, ...] = ("decode", "encode", "encode_argument", "default")
