"""Publish SPC panel events on the Home Assistant event bus.

Every FlexC EVENT the panel pushes is fired as a ``spc_flexc_event`` so that
automations can trigger on it and the logbook can show it. Only the fields
listed in ``EVENT_FIELDS`` are passed on; anything else in the panel's EVENT
record is dropped, including card numbers (``CARD_NUM``) sent with event 3014.
"""

from __future__ import annotations

from datetime import tzinfo
from typing import Any

from homeassistant.core import HomeAssistant

from .flexc.event_table import event_description

EVENT_SPC_FLEXC = "spc_flexc_event"

# Panel EVENT attribute -> event data key, and how the value is converted.
EVENT_FIELDS: dict[str, tuple[str, str]] = {
    "EV_ID": ("event_id", "int"),
    "EV_SEQ": ("sequence", "int"),
    "EV_GRP": ("event_group", "int"),
    "EV_DESC": ("panel_text", "str"),
    "SIA_CODE": ("sia_code", "str"),
    "SIA_ADDRESS": ("sia_address", "str"),
    "AREA_ID": ("area_id", "int"),
    "AREA_NAME": ("area_name", "str"),
    "ZONE_ID": ("zone_id", "int"),
    "ZONE_NAME": ("zone_name", "str"),
    "DOOR_ID": ("door_id", "int"),
    "DOOR_NAME": ("door_name", "str"),
    "USER_ID": ("user_id", "int"),
    "USER_NAME": ("user_name", "str"),
    "MG_ID": ("mapping_gate_id", "int"),
    "MG_NAME": ("mapping_gate_name", "str"),
    "KEYPAD_ID": ("keypad_id", "int"),
    "KEYPAD_NAME": ("keypad_name", "str"),
    "ACC_DENIED_REASON": ("access_denied_reason", "int"),
    "CID_CODE": ("cid_code", "str"),
    "CID_QUAL": ("cid_qualifier", "str"),
}


def _int_or_none(value: object) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def build_event_data(
    entry_id: str,
    event: dict[str, str],
    description: str | None,
    timezone: tzinfo,
) -> dict[str, Any]:
    """Return the event data fired for one panel EVENT record."""
    from .coordinator import _spc_datetime

    data: dict[str, Any] = {"entry_id": entry_id}
    for source, (key, kind) in EVENT_FIELDS.items():
        if source not in event:
            continue
        value = event[source]
        data[key] = _int_or_none(value) if kind == "int" else str(value).strip()
    data["description"] = description
    panel_time = _spc_datetime(event.get("TIMESTAMP"), timezone)
    data["panel_time"] = None if panel_time is None else panel_time.isoformat()
    return data


def async_fire_panel_event(
    hass: HomeAssistant,
    entry_id: str,
    event: dict[str, str],
    timezone: tzinfo,
) -> dict[str, Any]:
    """Fire ``spc_flexc_event`` for one panel EVENT record; return its data."""
    event_id = _int_or_none(event.get("EV_ID"))
    description = event_description(event_id, hass.config.language)
    data = build_event_data(entry_id, event, description, timezone)
    hass.bus.async_fire(EVENT_SPC_FLEXC, data)
    return data
