from functools import wraps
from typing import Protocol, TYPE_CHECKING, Callable, TypeVar, ParamSpec

P = ParamSpec("P")
R = TypeVar("R")


if TYPE_CHECKING:

    from ._types import EncodingSpecified

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


__all__: tuple[str, ...] = ("decode",)
