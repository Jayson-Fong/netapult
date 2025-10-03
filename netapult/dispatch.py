from importlib.metadata import entry_points
from typing import TYPE_CHECKING, Any

import netapult.client
import netapult.channel
import netapult.util
import netapult.exceptions

if TYPE_CHECKING:
    # noinspection PyProtectedMember
    from importlib.metadata import EntryPoints

DEVICE_TYPES: "EntryPoints" = entry_points(group="netapult.device")
PROTOCOLS: "EntryPoints" = entry_points(group="netapult.protocol")


def _extract_requested_class(
    name: str, builtins: "EntryPoints", overrides: dict[str, str | type] | None
) -> type | None:
    if overrides is not None and name in overrides:
        requested_class: str | type[netapult.client.Client] = overrides[name]
        if isinstance(requested_class, str):
            requested_class: type[netapult.client.Client] = (
                netapult.util.load_named_object(requested_class)
            )

        return requested_class

    try:
        return builtins[name].load()
    except KeyError:
        return None


def dispatch(
    device_type: str,
    protocol: str,
    device_overrides: dict[str, str | type[netapult.client.Client]] | None = None,
    protocol_overrides: dict[str, str | type] | None = None,
    protocol_options: dict[str, Any] | None = None,
    **kwargs,
) -> netapult.client.Client:
    client_class: type[netapult.client.Client] | None = _extract_requested_class(
        device_type, DEVICE_TYPES, device_overrides
    )

    if client_class is None:
        raise netapult.exceptions.DispatchException(
            f"Unknown device type: {device_type}"
        )

    protocol_class: type[netapult.channel.Channel] | None = _extract_requested_class(
        protocol, PROTOCOLS, protocol_overrides
    )

    if protocol_class is None:
        raise netapult.exceptions.DispatchException(f"Unknown protocol: {protocol}")

    return client_class(
        channel=protocol_class(protocol, **(protocol_options or {})), **kwargs
    )
