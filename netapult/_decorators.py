"""
Decorators

These decorators are meant for internal use only.
"""

import inspect
from functools import wraps
from typing import Protocol, TYPE_CHECKING, Callable, TypeVar, ParamSpec, Any

from .constants import DEFAULT

P = ParamSpec("P")
R = TypeVar("R")


if TYPE_CHECKING:
    # pylint: disable=too-few-public-methods
    class EncodingSpecified(Protocol):
        """Has encoding and errors instance attributes for byte encoding/decoding"""

        encoding: str
        errors: str

    # pylint: disable=too-few-public-methods
    class DecodeNormalizer(Protocol[P, R]):
        """
        Expected arguments for a method with the `decode` decorator.
        """

        def __call__(
            self: "EncodingSpecified",
            *args: P.args,
            text: bool = False,
            **kwargs: P.kwargs,
        ) -> R: ...


def decode(func: Callable[P, R]) -> Callable[P, R] | "DecodeNormalizer[P, R]":
    """
    Provides a wrapper to decode byte or bytearray return values.

    :param func: Method within an `EncodingSpecified`-compliant class.
    :return: Wrapper function.
    """

    @wraps(func)
    def wrapper(
        self: "EncodingSpecified", *args: P.args, text: bool = False, **kwargs: P.kwargs
    ) -> R:
        """
        Decodes byte and bytearray return values.

        :param self: `EncodingSpecified` instance.
        :param args: Arguments to pass to `func`.
        :param text: Whether to decode values to strings.
        :param kwargs: Keyword arguments to pass to `func`.
        :return: Result of `func`, with bytes and bytearrays decoded if `text` is True.
        """

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
    """
    Provides a wrapper to encode string arguments to bytes.

    :param func: Method within an `EncodingSpecified`-compliant class.
    :return: Wrapper function.
    """

    @wraps(func)
    def wrapper(self: "EncodingSpecified", *args: P.args, **kwargs: P.kwargs) -> R:
        """
        Encodes string arguments to bytes.

        :param self: `EncodingSpecified` instance.
        :param args: Arguments to pass to `func`.
        :param kwargs: Keyword arguments to pass to `func`.
        :return: Result of `func`, with strings encoded to bytes.
        """

        def _encode(value: Any) -> Any:
            """
            Encodes string arguments to bytes.

            :param value: Value to normalize.
            :return: `value` encoded to bytes if a string, otherwise the original `value`.
            """

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
    """
    Provides a decorator that encodes arguments to bytes.

    Expects that the call contains arguments for `encoding` and
    `errors` parameters, used for encoding strings to bytes. Only
    parameters specified in `encode_args` are normalized.

    :param encode_args: Argument names to encode.
    :return: Decorator that encodes arguments to bytes.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        """
        Provides a wrapper to encode strings to bytes.

        :param func: Function to wrap with an `encoding` and `errors` argument.
        :return: Wrapper function.
        """

        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            """
            Encodes string arguments to bytes.

            :param args: Arguments to pass to `func`.
            :param kwargs: Keyword arguments to pass to `func`.
            :return: Result of `func`, with strings encoded to bytes.
            """

            sig: inspect.Signature = inspect.signature(func)
            bound: inspect.BoundArguments = sig.bind(*args, **kwargs)
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
    """
    Provides a decorator that applies default values to a function call.

    :param normalization_kwargs: Mapping of function parameter names to attribute names.
    :return: Decorator that applies default values to a function call.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        """
        Provides a wrapper that applies default values to a function call.

        :param func: Function to wrap.
        :return: Wrapper function.
        """

        def wrapper(self: object, *args: P.args, **kwargs: P.kwargs) -> R:
            """
            Applies default values to a function call.

            For parameters enumerated in `normalization_kwargs` where the
            corresponding argument value is `DEFAULT`, replaces the argument
            with a value extracted from `self` named by the value corresponding
            to the parameter name in `normalization_kwargs`.

            :param self: Object to extract attributes from.
            :param args: Arguments to pass to `func`.
            :param kwargs: Keyword arguments to pass to `func`.
            :return: Result of `func`.
            """

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
