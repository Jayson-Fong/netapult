from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    # pylint: disable=too-few-public-methods
    class EncodingSpecified(Protocol):

        encoding: str
        errors: str
