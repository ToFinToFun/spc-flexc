"""Zone configuration: GET_ZONE_CONFIG and EDIT_ZONE (checked 2026-11-13).

GET_ZONE_CONFIG ID="n" reads a zone's record with any login. EDIT_ZONE takes
the whole record with ``ID`` and is accepted only from the engineer login
while the panel is in installer mode (otherwise ``65``). A record with a
field missing is refused with ``17`` and changes nothing. A change that is
accepted gets an empty FLEXML_REPLY without a reply element; SAVE_CONFIG
must follow, as for every configuration change.
"""

from __future__ import annotations

import re
from xml.sax.saxutils import quoteattr

from .flexml import (
    FlexMLError,
    FlexMLReplyError,
    _build_command_envelope,
    _parse_reply_root,
    describe_result,
)

ZONE_RECORD_FIELDS = (
    "ID",
    "TYPE",
    "NAME",
    "ATTRIB",
    "KEYARM_FUNC",
    "AREA",
    "TECHDELAY",
)
ZONE_NAME_MAX = 16  # the web page's MAXLENGTH for a zone description

# Zone types as the web page's Sektionstyp list (value = TYPE).
ZONE_TYPES: dict[int, str] = {
    0: "alarm",
    1: "entry_exit",
    2: "exit_terminator",
    3: "fire",
    4: "fire_exit",
    5: "line",
    6: "panic",
    7: "holdup",
    8: "tamper",
    9: "technical",
    10: "medical",
    11: "keyarm",
    12: "unused",
    13: "shunt",
    14: "x_shunt",
    15: "fault",
    16: "lock_supervision",
    17: "seismic",
    18: "all_okay",
    19: "holdup_fault",
    20: "warning_fault",
    21: "setting_authorisation",
    22: "lock_element",
    23: "glassbreak",
    24: "water",
    25: "heat",
    26: "freezer",
    27: "gas",
    28: "sprinkler",
    29: "co",
    30: "entry_exit_2",
}

# ATTRIB bits, mapped on the web page's zone attributes (FLEXC_PROTOCOL.md).
ZONE_ATTRIBUTES: dict[str, int] = {
    "access": 0x00000001,
    "exclude_a": 0x00000002,
    "exclude_b": 0x00000004,
    "24_hour": 0x00000008,
    "local": 0x00000010,
    "double_knock": 0x00000020,
    "chime": 0x00000040,
    "inhibit": 0x00000080,
    "normally_open": 0x00000100,
    "silent": 0x00000200,
    "log": 0x00000400,
    "open_only": 0x00000800,
    "report_only": 0x00001000,
    "final_exit": 0x00002000,
    "keyarm_set": 0x00004000,
    "keyarm_unset": 0x00008000,
    "shunt": 0x00010000,
    "report": 0x00020000,
    "display": 0x00040000,
    "audible": 0x00080000,
    "report_when_set": 0x00200000,
    "frequent": 0x00400000,
    "fire_prealarm": 0x00800000,
    "fire_recognition": 0x01000000,
    "exit_open": 0x02000000,
    "unset_local": 0x08000000,
    "keyarm_delayed": 0x10000000,
    "forced_set": 0x20000000,
    "auto_restore": 0x40000000,
    "no_bells": 0x80000000,
}

# KEYARM_FUNC values: what a key-arm zone does.
KEYARM_FUNCTIONS: dict[int, str] = {1: "partset_a", 2: "partset_b", 3: "fullset"}


def build_get_zone_config_command(zone_id: int, username: str, password: str) -> str:
    """Build CMD_GET_ZONE_CONFIG for one zone."""
    return _build_command_envelope(
        f'<CMD_GET_ZONE_CONFIG ID="{int(zone_id)}" />', username, password
    )


def parse_zone_config(response: str, zone_id: int) -> dict[str, str]:
    """Return the zone's whole record from a GET_ZONE_CONFIG reply."""
    root = _parse_reply_root(response)
    reply = root.find("REPLY_GET_ZONE_CONFIG")
    if reply is None:
        raise FlexMLError("No REPLY_GET_ZONE_CONFIG in the reply")
    if reply.get("RESULT") != "0":
        raise FlexMLReplyError(
            f"GET_ZONE_CONFIG failed: {describe_result(reply.get('RESULT'))}"
        )
    for zone in reply.iter("ZONE"):
        if zone.get("ID") == str(int(zone_id)):
            record = dict(zone.attrib)
            missing = [field for field in ZONE_RECORD_FIELDS if field not in record]
            if missing:
                raise FlexMLError(f"Zone {zone_id} record lacks {missing}")
            return record
    raise FlexMLError(f"Zone {zone_id} not in the GET_ZONE_CONFIG reply")


def zone_attribute_names(attrib: str) -> list[str]:
    """Names of the ATTRIB bits that are set."""
    value = int(attrib, 16)
    return [name for name, bit in ZONE_ATTRIBUTES.items() if value & bit]


def apply_zone_changes(
    record: dict[str, str],
    *,
    name: str | None = None,
    zone_type: int | None = None,
    area: int | None = None,
    techdelay: int | None = None,
    keyarm_function: int | None = None,
    attributes_on: list[str] | None = None,
    attributes_off: list[str] | None = None,
) -> dict[str, str]:
    """Return the whole record with the requested changes."""
    updated = {field: record[field] for field in ZONE_RECORD_FIELDS}
    if name is not None:
        if not name or len(name) > ZONE_NAME_MAX:
            raise ValueError(f"A zone name has 1 to {ZONE_NAME_MAX} characters")
        updated["NAME"] = name
    if zone_type is not None:
        if zone_type not in ZONE_TYPES:
            raise ValueError(f"Unknown zone type {zone_type}")
        updated["TYPE"] = str(zone_type)
    if area is not None:
        if not 1 <= area <= 64:
            raise ValueError(f"Unknown area {area}")
        updated["AREA"] = str(area)
    if techdelay is not None:
        if not 0 <= techdelay <= 9999:
            raise ValueError("The technical delay is 0 to 9999")
        updated["TECHDELAY"] = str(techdelay)
    if keyarm_function is not None:
        if keyarm_function not in KEYARM_FUNCTIONS:
            raise ValueError(f"Unknown key-arm function {keyarm_function}")
        updated["KEYARM_FUNC"] = str(keyarm_function)
    on = attributes_on or []
    off = attributes_off or []
    unknown = [attr for attr in (*on, *off) if attr not in ZONE_ATTRIBUTES]
    if unknown:
        raise ValueError(f"Unknown zone attributes {unknown}")
    if set(on) & set(off):
        raise ValueError("An attribute cannot be both set and cleared")
    value = int(updated["ATTRIB"], 16)
    for attr in on:
        value |= ZONE_ATTRIBUTES[attr]
    for attr in off:
        value &= ~ZONE_ATTRIBUTES[attr]
    updated["ATTRIB"] = f"{value:08X}"
    return updated


def build_edit_zone_command(
    record: dict[str, str], username: str, password: str
) -> str:
    """Build CMD_EDIT_ZONE with the whole record (send with the engineer login)."""
    missing = [field for field in ZONE_RECORD_FIELDS if field not in record]
    if missing:
        raise ValueError(f"EDIT_ZONE needs the whole record; missing {missing}")
    attributes = " ".join(
        f"{field}={quoteattr(str(record[field]))}" for field in ZONE_RECORD_FIELDS
    )
    return _build_command_envelope(
        f"<CMD_EDIT_ZONE {attributes} />", username, password
    )


def parse_edit_zone_reply(response: str) -> None:
    """Raise if the panel refused EDIT_ZONE; an empty reply means accepted."""
    root = _parse_reply_root(response)
    reply = root.find("REPLY_EDIT_ZONE")
    if reply is None:
        if re.search(r"<REPLY_", response or ""):
            raise FlexMLError("Unexpected reply to EDIT_ZONE")
        return
    if reply.get("RESULT") != "0":
        raise FlexMLReplyError(
            f"EDIT_ZONE failed: {describe_result(reply.get('RESULT'))}"
        )
