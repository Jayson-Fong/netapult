from contextlib import contextmanager
from typing import Protocol, runtime_checkable


@runtime_checkable
class SupportsPrivilege(Protocol):

    def enter_privilege(self): ...

    def exit_privilege(self): ...

    @contextmanager
    def privilege(self): ...
