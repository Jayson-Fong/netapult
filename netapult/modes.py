"""
Mode specifications to check if a Client supports a feature.
"""

from contextlib import contextmanager
from typing import Protocol, runtime_checkable


@runtime_checkable
class SupportsPrivilege(Protocol):
    """
    Client supporting privilege escalation.
    """

    def enter_privilege(self, *args, **kwargs) -> bool:
        """
        Attempt to enter a privileged state.
        """

    def exit_privilege(self, *args, **kwargs) -> bool:
        """
        Assuming `enter_privilege` was previously called, exit the privileged state.
        """

    @contextmanager
    def privilege(self):
        """
        Context manager for acquiring privilege.

        :yields: Self.
        """


__all__: tuple[str, ...] = ("SupportsPrivilege",)
