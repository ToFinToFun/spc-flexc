"""Home Assistant device helpers for SPC FlexC."""

from typing import Any, cast

from homeassistant.const import CONF_HOST
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo

from ..const import CONF_DOOR_CONTROLLERS, CONF_WIRELESS_ZONES, DOMAIN
from ..coordinator import SpcFlexCCoordinator

# How entities are grouped into devices (owner's design, 2026-11-11):
# the panel and the X-BUS hardware form the device tree; doors are devices
# under their door controller. Zones sit on the hardware their input is on:
# panel inputs 1-8, I/O expander with address n zones 8n+1..8n+8 (Vanderbilt
# manual, "Addressing Mode"), a door's zone on the door. Door controller
# zones are freely numbered by the panel and are not reported over FlexC, so
# they stay on the panel. Areas, users, calendars and logs are logical and
# live on the panel device.
XBUS_IO_EXPANDER = 2
XBUS_DOOR_CONTROLLER = 6
PANEL_INPUTS = 8


def build_panel_device_info(
    coordinator: SpcFlexCCoordinator,
) -> DeviceInfo:
    """Return the main SPC panel device information."""
    panel = coordinator.data.panel

    serial = panel.serial_number or coordinator.entry.entry_id
    name = panel.installation_name or "SPC"

    if panel.spc_variant:
        model = f"SPC{panel.spc_variant}"
    else:
        model = panel.spc_type or "SPC"

    return DeviceInfo(
        identifiers={(DOMAIN, str(serial))},
        name=name,
        manufacturer="Vanderbilt",
        model=model,
        serial_number=str(serial),
        sw_version=panel.firmware_version,
        hw_version=panel.hardware_version,
        configuration_url=f"http://{coordinator.entry.data[CONF_HOST]}",
    )


def build_area_device_info(
    coordinator: SpcFlexCCoordinator,
    area_id: int,
) -> DeviceInfo:
    """Return the Home Assistant device for one SPC area."""
    panel = coordinator.data.panel
    area = coordinator.data.areas[area_id]

    serial = panel.serial_number or coordinator.entry.entry_id

    device_info = DeviceInfo(
        identifiers={(DOMAIN, f"{serial}_area_{area_id}")},
        name=area.name or f"Area {area_id}",
        manufacturer="Vanderbilt",
        model="SPC Area",
    )

    _set_parent_device(coordinator, device_info, (DOMAIN, str(serial)))
    return device_info


def door_controller_serial(
    coordinator: SpcFlexCCoordinator, door_id: int
) -> str | None:
    """Return the serial of the door controller a door is on, if known.

    FlexC does not report which door controller a door is on, so the owner's
    choice in the options wins. Without one, the answer is only certain when
    the panel has a single door controller; with several the door stays on
    the panel rather than under a guessed controller (the numbering "doors
    2n-1 and 2n on controller n" did not hold on the reference panel).
    """
    devices = coordinator.data.xbus_devices
    chosen = (coordinator.entry.options.get(CONF_DOOR_CONTROLLERS) or {}).get(
        str(door_id)
    )
    if chosen in devices:
        return str(chosen)
    controllers = [
        serial
        for serial, device in devices.items()
        if device.device_type == XBUS_DOOR_CONTROLLER
    ]
    return str(controllers[0]) if len(controllers) == 1 else None


def build_door_device_info(
    coordinator: SpcFlexCCoordinator,
    door_id: int,
) -> DeviceInfo:
    """Return the device of one door, under its door controller."""
    panel = coordinator.data.panel
    door = coordinator.data.doors[door_id]
    serial = panel.serial_number or coordinator.entry.entry_id

    device_info = DeviceInfo(
        identifiers={(DOMAIN, f"{serial}_door_{door_id}")},
        name=door.name or door.zone_name or f"Door {door_id}",
        manufacturer="Vanderbilt",
        model="SPC Door",
    )

    controller = door_controller_serial(coordinator, door_id)
    parent_identifier = (
        (DOMAIN, f"{serial}_xbus_{controller}")
        if controller is not None
        else (DOMAIN, str(serial))
    )
    _set_parent_device(coordinator, device_info, parent_identifier)
    return device_info


def xbus_serial_as_shown(serial: str | None) -> str | None:
    """X-BUS serials come as hex over FlexC; the web page shows them decimal."""
    try:
        return str(int(serial, 16)) if serial else serial
    except ValueError:
        return serial


def zone_placeholders(zone_id: int, zone: Any) -> dict[str, str]:
    """Placeholders for a zone's entity names ("Zone 9 Hall – Inhibit")."""
    return {"zone_id": str(zone_id), "zone_name": getattr(zone, "name", None) or ""}


def door_placeholders(coordinator: SpcFlexCCoordinator, door_id: int) -> dict[str, str]:
    """Placeholders for a door's entity names ("Door 3 Entrance – Block")."""
    door = coordinator.data.doors.get(door_id)
    name = (door.name or door.zone_name) if door is not None else None
    return {"door_id": str(door_id), "door_name": name or ""}


def numbered(number: int, name: str | None, fallback: str = "Zone") -> str:
    """Name an object like the panel's web pages do: number first ("9 Hall")."""
    return f"{number} {name}" if name else f"{fallback} {number}"


def zone_hardware(coordinator: SpcFlexCCoordinator, zone_id: int) -> tuple[str, Any]:
    """Return where a zone's input is: ("door", id), ("xbus", serial) or ("panel", None)."""
    for door_id, door in coordinator.data.doors.items():
        if door.zone_id == zone_id:
            return "door", door_id
    if 1 <= zone_id <= PANEL_INPUTS:
        return "panel", None
    for serial, device in coordinator.data.xbus_devices.items():
        if device.device_type != XBUS_IO_EXPANDER or not device.device_id:
            continue
        first = device.device_id * 8 + 1
        if first <= zone_id < first + (device.input_count or 8):
            return "xbus", serial
    if getattr(coordinator.data, "wireless_receiver", False):
        chosen = coordinator.entry.options.get(CONF_WIRELESS_ZONES)
        if chosen is None or str(zone_id) in {str(z) for z in chosen}:
            return "wireless", None
    return "panel", None


def build_wireless_device_info(coordinator: SpcFlexCCoordinator) -> DeviceInfo:
    """Return the device of the panel's wireless receiver."""
    panel = coordinator.data.panel
    serial = panel.serial_number or coordinator.entry.entry_id
    device_info = DeviceInfo(
        identifiers={(DOMAIN, f"{serial}_wireless")},
        translation_key="wireless_receiver",
        manufacturer="Vanderbilt",
        model="SPC wireless receiver",
    )
    _set_parent_device(coordinator, device_info, (DOMAIN, str(serial)))
    return device_info


def zone_input(coordinator: SpcFlexCCoordinator, zone_id: int) -> dict[str, Any]:
    """Where a zone's input is: board, input number and how it is known."""
    kind, key = zone_hardware(coordinator, zone_id)
    if kind == "door":
        door = coordinator.data.doors[key]
        return {
            "input_board": door.name or door.zone_name or f"Door {key}",
            "input_number": None,
            "input_known_from": "door",
        }
    if kind == "wireless":
        return {
            "input_board": "Wireless receiver",
            "input_number": None,
            "input_known_from": "assumed wireless",
        }
    if kind == "xbus":
        device = coordinator.data.xbus_devices[key]
        return {
            "input_board": device.name,
            "input_number": zone_id - device.device_id * 8,
            "input_known_from": "address rule",
        }
    if 1 <= zone_id <= PANEL_INPUTS:
        return {
            "input_board": "Controller",
            "input_number": zone_id,
            "input_known_from": "address rule",
        }
    return {"input_board": None, "input_number": None, "input_known_from": "unknown"}


def build_zone_device_info(
    coordinator: SpcFlexCCoordinator, zone_id: int
) -> DeviceInfo:
    """Return the device of the hardware a zone's input is on."""
    kind, key = zone_hardware(coordinator, zone_id)
    if kind == "door":
        return build_door_device_info(coordinator, key)
    if kind == "xbus":
        return build_xbus_device_info(coordinator, key)
    if kind == "wireless":
        return build_wireless_device_info(coordinator)
    return build_panel_device_info(coordinator)


def _xbus_model(
    device_type: int | None, input_count: int | None, output_count: int | None
) -> str:
    """Return only empirically validated X-BUS family/model labels."""
    if device_type == 1:
        return "SPC Keypad"
    if device_type == 7:
        return "SPC Comfort Keypad"
    if device_type == 6 and input_count == 4 and output_count == 2:
        return "SPCA210 2-door expander"
    if device_type == 2:
        if input_count == 8 and output_count == 2:
            return "SPCE650 I/O expander (8 inputs / 2 outputs)"
        if input_count == 0 and output_count == 8:
            return "SPCE450 output expander (8 outputs)"
        return "SPC I/O expander"
    return "SPC X-BUS"


def build_xbus_device_info(
    coordinator: SpcFlexCCoordinator,
    serial_number: str,
) -> DeviceInfo:
    """Return a dedicated Home Assistant device for one X-BUS peripheral."""
    panel = coordinator.data.panel
    device = coordinator.data.xbus_devices[serial_number]
    panel_serial = panel.serial_number or coordinator.entry.entry_id

    device_info = DeviceInfo(
        identifiers={(DOMAIN, f"{panel_serial}_xbus_{serial_number}")},
        name=device.name or f"X-BUS {device.device_id}",
        manufacturer="Vanderbilt",
        model=_xbus_model(device.device_type, device.input_count, device.output_count),
        serial_number=xbus_serial_as_shown(device.serial_number),
        sw_version=device.version,
    )

    _set_parent_device(coordinator, device_info, (DOMAIN, str(panel_serial)))
    return device_info


def migrate_xbus_registry_identity(
    coordinator: SpcFlexCCoordinator,
    serial_number: str,
    entity_domain: str,
    entity_suffix: str,
) -> None:
    """Migrate a legacy local-ID X-BUS registry identity to its serial."""
    device = coordinator.data.xbus_devices[serial_number]
    same_id = [
        candidate
        for candidate in coordinator.data.xbus_devices.values()
        if candidate.device_id == device.device_id
    ]

    entry_id = coordinator.entry.entry_id
    old_unique_id = f"{entry_id}_xbus_{device.device_id}_{entity_suffix}"
    new_unique_id = f"{entry_id}_xbus_{serial_number}_{entity_suffix}"
    entity_registry = er.async_get(coordinator.hass)
    entity_id = entity_registry.async_get_entity_id(
        entity_domain, DOMAIN, old_unique_id
    )

    panel_serial = coordinator.data.panel.serial_number or entry_id
    old_identifier = (DOMAIN, f"{panel_serial}_xbus_{device.device_id}")
    new_identifier = (DOMAIN, f"{panel_serial}_xbus_{serial_number}")
    device_registry = dr.async_get(coordinator.hass)
    # The current Home Assistant DeviceRegistry API provides this helper, but
    # older pytest-homeassistant-custom-component type information may not yet
    # expose it to mypy.
    old_device = device_registry.async_get_device_by_identifier(  # type: ignore[attr-defined]
        old_identifier, entry_id
    )

    if len(same_id) == 1:
        if entity_id is not None:
            entity_registry.async_update_entity(entity_id, new_unique_id=new_unique_id)
        if old_device is not None:
            device_registry.async_update_device(
                old_device.id, new_identifiers={new_identifier}
            )
        return

    # A legacy local ID cannot identify one physical device when that ID is
    # reused. Remove only the obsolete X-BUS registry records; the serial-based
    # entities/devices created immediately afterwards are unambiguous.
    if entity_id is not None:
        entity_registry.async_remove(entity_id)
    # Do not remove the legacy device here. This helper runs once per entity
    # while Home Assistant is creating the new serial-based devices. Removing an
    # ambiguous legacy device during platform setup can detach entities that are
    # still being migrated or recreated. The serial-based DeviceInfo identifiers
    # will create the unambiguous devices without mutating that shared legacy
    # device.


def _set_parent_device(
    coordinator: SpcFlexCCoordinator,
    device_info: DeviceInfo,
    parent_identifier: tuple[str, str],
) -> None:
    """Attach a device using via_device_id when supported by Home Assistant."""
    get_device_id = getattr(dr, "async_get_device_id_by_identifier", None)

    if get_device_id is None:
        return

    parent_device_id = get_device_id(
        coordinator.hass,
        parent_identifier,
        config_entry_id=coordinator.entry.entry_id,
    )

    if parent_device_id is not None:
        cast(dict[str, Any], device_info)["via_device_id"] = parent_device_id
