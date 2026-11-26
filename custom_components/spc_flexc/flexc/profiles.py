"""User profiles: GET_USER_PROFILE_CONFIG, EDIT/ADD/DELETE_USER_PROFILE.

A ``USER_PROFILE_CONFIG`` record (SPC4300, firmware 3.14.1, read 2026-11-10)
has ``USER_PROFILE_ID``, ``GID``, ``NAME``, ``AREAS`` (16 hex digits, bit
``n-1`` = area ``n``), ``USER_RIGHTS`` and ``USER_RIGHTS2`` (8 hex digits
each, bit meaning not mapped yet), ``CALENDAR`` (``0`` = none), ``SITE_CODE``
and one ``DOOR<n>`` attribute for each door the profile has a setting for.
Doors without a setting have no attribute at all; the values seen are ``0``
and ``2`` (meaning not mapped yet).

``GET_USER_PROFILE_CONFIG USER_PROFILE_ID="0"`` returns every profile; one
ID returns that profile, an unused ID an empty reply. Without
``USER_PROFILE_ID`` the panel answers ``102``.

Profiles hold no secrets.

EDIT, ADD and DELETE are UNTESTED on a panel: they are built like
``EDIT_USER`` (whole record, read just before the edit) and ``DELETE_USER``
(ID only).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from xml.sax.saxutils import quoteattr

from .flexml import (
    FlexMLError,
    _build_command_envelope,
    _parse_reply_root,
    _validate_reply,
)

NAME_MAX = 16
AREA_COUNT = 64
DOOR_FIELD = re.compile(r"^DOOR(\d+)$")


@dataclass(frozen=True)
class SpcUserProfile:
    """A user profile as read from the panel."""

    profile_id: int
    name: str
    areas: tuple[int, ...] = ()
    calendar: int = 0
    user_rights: str = "00000000"
    user_rights2: str = "00000000"
    site_code: str = "0"
    doors: dict[int, str] = field(default_factory=dict)
    group_id: str = "0"


def build_user_profile_config_command(
    profile_id: int, username: str, password: str
) -> str:
    """Build CMD_GET_USER_PROFILE_CONFIG (USER_PROFILE_ID 0 = all profiles)."""
    return _build_command_envelope(
        f'<CMD_GET_USER_PROFILE_CONFIG USER_PROFILE_ID="{int(profile_id)}" />',
        username,
        password,
    )


def parse_user_profile_records(response: str) -> list[dict[str, str]]:
    """Return the raw USER_PROFILE_CONFIG records."""
    root = _parse_reply_root(response)
    reply = root.find("REPLY_GET_USER_PROFILE_CONFIG")
    if reply is None:
        raise FlexMLError("REPLY_GET_USER_PROFILE_CONFIG not found")
    _validate_reply(reply, "REPLY_GET_USER_PROFILE_CONFIG")
    return [dict(element.attrib) for element in reply.iter("USER_PROFILE_CONFIG")]


def areas_from_mask(mask: str) -> tuple[int, ...]:
    """Return the area IDs set in a hex area mask (bit n-1 = area n)."""
    try:
        value = int(mask or "0", 16)
    except ValueError:
        return ()
    return tuple(n for n in range(1, AREA_COUNT + 1) if value & (1 << (n - 1)))


def mask_from_areas(areas: list[int]) -> str:
    """Return the 16-hex-digit mask for a list of area IDs."""
    value = 0
    for area in areas:
        if not 1 <= int(area) <= AREA_COUNT:
            raise ValueError(f"Area {area} is outside 1-{AREA_COUNT}")
        value |= 1 << (int(area) - 1)
    return f"{value:016X}"


def user_profile(record: dict[str, str]) -> SpcUserProfile:
    """Build a profile from a raw record."""
    doors = {}
    for key, value in record.items():
        match = DOOR_FIELD.match(key)
        if match:
            doors[int(match.group(1))] = value
    try:
        calendar = int(record.get("CALENDAR", "0"))
    except ValueError:
        calendar = 0
    return SpcUserProfile(
        profile_id=int(record["USER_PROFILE_ID"]),
        name=record.get("NAME", "").strip(),
        areas=areas_from_mask(record.get("AREAS", "0")),
        calendar=calendar,
        user_rights=record.get("USER_RIGHTS", "00000000"),
        user_rights2=record.get("USER_RIGHTS2", "00000000"),
        site_code=record.get("SITE_CODE", "0"),
        doors=dict(sorted(doors.items())),
        group_id=record.get("GID", "0"),
    )


def apply_profile_changes(
    record: dict[str, str],
    *,
    name: str | None = None,
    areas: list[int] | None = None,
    calendar: int | None = None,
    doors: dict[int, str | None] | None = None,
) -> dict[str, str]:
    """Return a copy of a raw record with the given fields changed.

    ``doors`` maps a door ID to its new value; ``None`` removes the door's
    setting (the attribute is left out).
    """
    updated = dict(record)
    if name is not None:
        if not name or len(name) > NAME_MAX:
            raise ValueError(f"A profile name has 1-{NAME_MAX} characters")
        updated["NAME"] = name
    if areas is not None:
        updated["AREAS"] = mask_from_areas(areas)
    if calendar is not None:
        if int(calendar) < 0:
            raise ValueError("A calendar ID is 0 (none) or higher")
        updated["CALENDAR"] = str(int(calendar))
    for door_id, value in (doors or {}).items():
        key = f"DOOR{int(door_id)}"
        if value is None:
            updated.pop(key, None)
        else:
            updated[key] = str(value)
    return updated


def _attributes(record: dict[str, str]) -> str:
    return " ".join(f"{key}={quoteattr(value)}" for key, value in record.items())


def build_edit_user_profile_command(
    record: dict[str, str], username: str, password: str
) -> str:
    """Build CMD_EDIT_USER_PROFILE from a whole record. UNTESTED on a panel."""
    if "USER_PROFILE_ID" not in record:
        raise ValueError("EDIT_USER_PROFILE needs USER_PROFILE_ID")
    return _build_command_envelope(
        f"<CMD_EDIT_USER_PROFILE {_attributes(record)} />", username, password
    )


def build_add_user_profile_command(
    profile_id: int,
    name: str,
    areas: list[int],
    calendar: int,
    username: str,
    password: str,
) -> str:
    """Build CMD_ADD_USER_PROFILE. UNTESTED: attributes mirror the read record."""
    record = apply_profile_changes(
        {
            "USER_PROFILE_ID": str(int(profile_id)),
            "GID": "0",
            "USER_RIGHTS": "00000000",
            "USER_RIGHTS2": "00000000",
            "SITE_CODE": "0",
        },
        name=name,
        areas=areas,
        calendar=calendar,
    )
    return _build_command_envelope(
        f"<CMD_ADD_USER_PROFILE {_attributes(record)} />", username, password
    )


def build_delete_user_profile_command(
    profile_id: int, username: str, password: str
) -> str:
    """Build CMD_DELETE_USER_PROFILE. UNTESTED: only USER_PROFILE_ID is sent."""
    return _build_command_envelope(
        f'<CMD_DELETE_USER_PROFILE USER_PROFILE_ID="{int(profile_id)}" />',
        username,
        password,
    )
