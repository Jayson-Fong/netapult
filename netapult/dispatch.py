from importlib.metadata import entry_points
from typing import TYPE_CHECKING, Any


from . import exceptions as _exceptions

if TYPE_CHECKING:
    # noinspection PyProtectedMember
    from importlib.metadata import EntryPoints

    from . import channel as _channel
    from . import client as _client
    from . import util as _util

DEVICE_TYPES: "EntryPoints" = entry_points(group="netapult.device")
PROTOCOLS: "EntryPoints" = entry_points(group="netapult.protocol")


def _extract_requested_class(
    name: str, builtins: "EntryPoints", overrides: dict[str, str | type] | None
) -> type | None:
    if overrides is not None and name in overrides:
        requested_class: str | type["_client.Client"] = overrides[name]
        if isinstance(requested_class, str):
            requested_class: type["_client.Client"] = _util.load_object(requested_class)

        return requested_class

    try:
        return builtins[name].load()
    except KeyError:
        return None


def dispatch(
    device_type: str,
    protocol: str,
    device_overrides: dict[str, str | type["_client.Client"]] | None = None,
    protocol_overrides: dict[str, str | type] | None = None,
    protocol_options: dict[str, Any] | None = None,
    **kwargs,
) -> "_client.Client":
    client_class: type["_client.Client"] | None = _extract_requested_class(
        device_type, DEVICE_TYPES, device_overrides
    )

    if client_class is None:
        raise _exceptions.DispatchException(f"Unknown device type: {device_type}")

    protocol_class: type["_channel.Channel"] | None = _extract_requested_class(
        protocol, PROTOCOLS, protocol_overrides
    )

    if protocol_class is None:
        raise _exceptions.DispatchException(f"Unknown protocol: {protocol}")

    # noinspection PyArgumentList
    return client_class(
        channel=protocol_class(protocol, **(protocol_options or {})), **kwargs
    )


__all__: tuple[str, ...] = ("dispatch", "DEVICE_TYPES", "PROTOCOLS")
