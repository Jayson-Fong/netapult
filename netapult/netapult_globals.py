"""
Global value specification
"""


# noinspection PyPep8Naming
# pylint: disable=invalid-name,too-few-public-methods
class DEFAULT_TYPE:
    """
    Indicates that a value should be replaced with a default value.
    """


DEFAULT = DEFAULT_TYPE()


__all__: tuple[str, ...] = ("DEFAULT_TYPE", "DEFAULT")
