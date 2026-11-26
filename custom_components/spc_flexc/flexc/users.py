"""Panel users: GET_USER_CONFIG, EDIT_USER, ADD_USER, DELETE_USER, GET_USER_STATUS
and GET_UNKNOWN_CARDS.

A ``USER_CONFIG`` record (SPC4300, firmware 3.14.1) has ``USER_ID``, ``GID``,
``NAME``, ``PIN`` (encoded), ``CARD_NO``, ``CARD_ATTRIB``, ``USER_ATTRIB``,
``START_DATE``, ``END_DATE``, ``LANGUAGE``, ``USER_PROFILE_1``..``_5`` and
``WEBPASS_DATA``. ``GET_USER_CONFIG USER_ID="0"`` returns every user.

``PIN``, ``CARD_NO`` and ``WEBPASS_DATA`` are secrets. They are never kept in
the integration's state, never logged and never returned to Home Assistant.
``EDIT_USER`` needs the whole record, so the record is read just before an
edit, only the requested fields are changed, and it is sent back without
``WEBPASS_DATA`` (a web password is tied to the user name). The secrets only
live in memory for the duration of that call.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from xml.sax.saxutils import quoteattr

from .flexml import (
    FlexMLError,
    _build_command_envelope,
    _parse_reply_root,
    _validate_reply,
)

SECRET_FIELDS = frozenset({"PIN", "CARD_NO", "WEBPASS_DATA"})
# Card numbers are shown in Home Assistant like on the panel's web page
# (owner's decision 2026-11-11); PINs, PIN keys and web passwords never are.
# Never sent back with EDIT_USER: the web password is bound to the user name.
NOT_SENT_ON_EDIT = frozenset({"WEBPASS_DATA"})
PROFILE_FIELDS = tuple(f"USER_PROFILE_{n}" for n in range(1, 6))
NAME_MAX = 16


@dataclass(frozen=True)
class SpcUser:
    """A panel user without secrets."""

    user_id: int
    name: str
    profiles: tuple[int, ...] = ()
    start_date: str = "0"
    end_date: str = "0"
    language: str | None = None
    user_attrib: str | None = None
    card_attrib: str | None = None
    has_card: bool = False
    card_number: str | None = None
    card_flags: tuple[str, ...] = ()
    group_id: str = "0"
    raw_fields: tuple[str, ...] = field(default=())


def build_user_config_command(user_id: int, username: str, password: str) -> str:
    """Build CMD_GET_USER_CONFIG (USER_ID 0 = all users)."""
    return _build_command_envelope(
        f'<CMD_GET_USER_CONFIG USER_ID="{int(user_id)}" />', username, password
    )


def parse_user_records(response: str) -> list[dict[str, str]]:
    """Return the raw USER_CONFIG records, secrets included (internal use only)."""
    root = _parse_reply_root(response)
    reply = root.find("REPLY_GET_USER_CONFIG")
    if reply is None:
        raise FlexMLError("REPLY_GET_USER_CONFIG not found")
    _validate_reply(reply, "REPLY_GET_USER_CONFIG")
    return [dict(element.attrib) for element in reply.iter("USER_CONFIG")]


def public_user(record: dict[str, str]) -> SpcUser:
    """Build a user without secrets from a raw record."""
    profiles = []
    for name in PROFILE_FIELDS:
        try:
            value = int(record.get(name, "0"))
        except ValueError:
            continue
        if value:
            profiles.append(value)
    return SpcUser(
        user_id=int(record["USER_ID"]),
        name=record.get("NAME", "").strip(),
        profiles=tuple(profiles),
        start_date=record.get("START_DATE", "0"),
        end_date=record.get("END_DATE", "0"),
        language=record.get("LANGUAGE"),
        user_attrib=record.get("USER_ATTRIB"),
        card_attrib=record.get("CARD_ATTRIB"),
        has_card=bool(record.get("CARD_NO", "").strip().strip("0")),
        card_number=(record.get("CARD_NO") or "").strip().lstrip("0") or None,
        card_flags=tuple(card_flags(record.get("CARD_ATTRIB"))),
        group_id=record.get("GID", "0"),
        raw_fields=tuple(sorted(k for k in record if k not in SECRET_FIELDS)),
    )


# CARD_ATTRIB bits, mapped on an SPC4300 (3.14.1) on 2026-11-11 by switching
# each option of the web page's user "Passerkontroll" on alone and reading
# GET_USER_CONFIG. Bit 0x01 was never seen.
CARD_FLAGS: dict[str, int] = {
    "extended_time": 0x02,  # Förlängd tid
    "pin_bypass": 0x04,  # PIN förbikoppling
    "priority": 0x08,  # Prioritet
    "escort": 0x10,  # Vittne
    "custodian": 0x20,  # Ledsagare
    "card_blocked": 0x40,  # Spärra kort
}
CARD_NUMBER_MAX = 0xFFFFFFFF


def card_flags(card_attrib: str | None) -> list[str]:
    """Return the names of the card options set in CARD_ATTRIB."""
    try:
        value = int(card_attrib or "0", 16)
    except ValueError:
        return []
    return [name for name, bit in CARD_FLAGS.items() if value & bit]


def card_attrib_with(card_attrib: str | None, changes: dict[str, bool]) -> str:
    """Return CARD_ATTRIB with the given card options switched on or off."""
    try:
        value = int(card_attrib or "0", 16)
    except ValueError:
        value = 0
    for name, on in changes.items():
        bit = CARD_FLAGS[name]
        value = value | bit if on else value & ~bit
    return f"{value:02X}"


def check_card_number(card_number: str) -> str:
    """Return a card number as the panel keeps it (decimal, 0 = no card)."""
    text = str(card_number).strip()
    if not text.isdigit() or int(text) > CARD_NUMBER_MAX:
        raise ValueError("A card number is 0-4294967295 (0 removes the card)")
    return str(int(text))


def apply_user_changes(
    record: dict[str, str],
    *,
    name: str | None = None,
    profiles: list[int] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    card_number: str | None = None,
    card_options: dict[str, bool] | None = None,
    language: int | None = None,
) -> dict[str, str]:
    """Return a copy of a raw record with the given non-secret fields changed."""
    updated = dict(record)
    if name is not None:
        if not name or len(name) > NAME_MAX:
            raise ValueError(f"A user name has 1-{NAME_MAX} characters")
        updated["NAME"] = name
    if profiles is not None:
        if len(profiles) > len(PROFILE_FIELDS):
            raise ValueError("A user has at most 5 profiles")
        for index, field_name in enumerate(PROFILE_FIELDS):
            updated[field_name] = (
                str(int(profiles[index])) if index < len(profiles) else "0"
            )
    if start_date is not None:
        updated["START_DATE"] = start_date
    if end_date is not None:
        updated["END_DATE"] = end_date
    if card_number is not None:
        updated["CARD_NO"] = check_card_number(card_number)
    if card_options:
        updated["CARD_ATTRIB"] = card_attrib_with(
            updated.get("CARD_ATTRIB"), card_options
        )
    if language is not None:
        if not 0 <= int(language) <= 255:
            raise ValueError("A language is 0-255 (255 = the system language)")
        updated["LANGUAGE"] = str(int(language))
    return updated


# START_DATE / END_DATE: day number with 1 January 2000 as day 1, "0" = no
# date limit.
# Checked on an SPC4300 (3.14.1) on 2026-11-11: the web page's "Datumbegränsad"
# 1 Dec 2026 - 24 Dec 2026 read back as START_DATE="9832" END_DATE="9855".
SPC_DATE_EPOCH = date(1999, 12, 31)  # day 0


def spc_day(value: date) -> str:
    """Return a date as the panel's day number."""
    days = (value - SPC_DATE_EPOCH).days
    if days < 1:
        raise ValueError("A validity date must be after 1 January 2000")
    return str(days)


def spc_date(value: str | None) -> date | None:
    """Return the date of a panel day number; ``None`` for 0 (no limit)."""
    try:
        days = int(value or "0")
    except ValueError:
        return None
    return SPC_DATE_EPOCH + timedelta(days=days) if days > 0 else None


def validity_dates(start: date | None, end: date | None) -> tuple[str, str]:
    """Return START_DATE and END_DATE for a validity period (both or neither)."""
    if start is None and end is None:
        return "0", "0"
    if start is None or end is None:
        raise ValueError("A validity period needs both a start and an end date")
    if end < start:
        raise ValueError("The end date is before the start date")
    return spc_day(start), spc_day(end)


def build_language_config_command(username: str, password: str) -> str:
    """Build CMD_READ_LANG_CFG (no attributes; checked on an SPC4300)."""
    return _build_command_envelope("<CMD_READ_LANG_CFG />", username, password)


def parse_installed_languages(response: str) -> list[int]:
    """Return the language numbers installed on the panel (LANGUAGES bit mask).

    The owner's panel answered LANGUAGES="00000081": languages 0 and 7, and
    its users use 7 for Swedish; 255 on a user means the system language.
    """
    root = _parse_reply_root(response)
    reply = root.find("REPLY_READ_LANG_CFG")
    if reply is None:
        raise FlexMLError("REPLY_READ_LANG_CFG not found")
    _validate_reply(reply, "REPLY_READ_LANG_CFG")
    status = reply.find("LANGUAGE_STATUS")
    try:
        mask = int((status.get("LANGUAGES") if status is not None else "") or "0", 16)
    except ValueError:
        return []
    return [bit for bit in range(32) if mask & (1 << bit)]


PIN_PATTERN = re.compile(r"^\d{4,8}$")


def _check_pin(pin: str) -> None:
    if not PIN_PATTERN.match(pin):
        raise ValueError("A PIN has 4-8 digits")


def pin_key(stored: str, pin: str) -> str:
    """Return a user's PIN key (8 hex digits) from the stored value and its PIN.

    The key belongs to the user number: it stays the same when the PIN
    changes and when the user is deleted and created again (checked on an
    SPC4300, 3.14.1). It is as secret as the PIN.
    """
    _check_pin(pin)
    try:
        return f"{int(stored, 16) ^ int(pin):08X}"
    except ValueError as err:
        raise ValueError("The stored PIN has an unknown format") from err


def encode_pin(key: str, pin: str) -> str:
    """Return the value the panel stores for a PIN, given the user's key."""
    _check_pin(pin)
    return f"{int(key, 16) ^ int(pin):08X}"


def recode_pin(stored: str, current_pin: str, new_pin: str) -> str:
    """Return the stored PIN value for new_pin, given the current one.

    The panel stores a PIN as 8 hex digits: the PIN as an integer XOR a key
    that is fixed for each user (checked on an SPC4300, 3.14.1). The key is
    ``stored ^ current_pin``. A wrong current PIN gives a wrong key and so an
    unknown new PIN; the owner can then set it in the web interface.
    """
    for pin in (current_pin, new_pin):
        if not PIN_PATTERN.match(pin):
            raise ValueError("A PIN has 4-8 digits")
    try:
        key = int(stored, 16) ^ int(current_pin)
    except ValueError as err:
        raise ValueError("The stored PIN has an unknown format") from err
    return f"{key ^ int(new_pin):08X}"


def build_edit_user_command(
    record: dict[str, str], username: str, password: str
) -> str:
    """Build CMD_EDIT_USER from a whole record (without WEBPASS_DATA)."""
    if "USER_ID" not in record:
        raise ValueError("EDIT_USER needs USER_ID")
    attributes = " ".join(
        f"{key}={quoteattr(value)}"
        for key, value in record.items()
        if key not in NOT_SENT_ON_EDIT
    )
    return _build_command_envelope(
        f"<CMD_EDIT_USER {attributes} />", username, password
    )


def build_add_user_command(
    user_id: int,
    name: str,
    profiles: list[int],
    encoded_pin: str,
    username: str,
    password: str,
    start_date: str = "0",
    end_date: str = "0",
    card_number: str | None = None,
    language: int | None = None,
) -> str:
    """Build CMD_ADD_USER with the whole record (checked on an SPC4300).

    ``encoded_pin`` is the PIN encoded with the key of this user number
    (``encode_pin``); with a wrongly encoded PIN the panel answers ``59``,
    without a PIN ``17``. The record mirrors GET_USER_CONFIG without GID and
    WEBPASS_DATA; the panel gives a new user no card.
    """
    record = apply_user_changes(
        {
            "USER_ID": str(int(user_id)),
            "NAME": "",
            "PIN": encoded_pin,
            "CARD_NO": "0",
            "CARD_ATTRIB": "00",
            "USER_ATTRIB": "0",
            "START_DATE": "0",
            "END_DATE": "0",
            "LANGUAGE": "255",
        },
        name=name,
        profiles=profiles,
        start_date=start_date,
        end_date=end_date,
        card_number=card_number,
        language=language,
    )
    attributes = " ".join(f"{key}={quoteattr(value)}" for key, value in record.items())
    return _build_command_envelope(f"<CMD_ADD_USER {attributes} />", username, password)


def build_delete_user_command(user_id: int, username: str, password: str) -> str:
    """Build CMD_DELETE_USER (only USER_ID; checked on an SPC4300)."""
    return _build_command_envelope(
        f'<CMD_DELETE_USER USER_ID="{int(user_id)}" />', username, password
    )


# GET_USER_STATUS (read on the panel 2026-11-10, test user 99): one
# GET_USER_STATUS element with GROUP_SIDE_MASK, GROUP_SIDE_VALID_MASK,
# INVALID_PIN_COUNT, USER_ALERTS_STATE, USER_ALERTS_STATUS,
# USER_ALERTS_ACCEPTED, FOB_LOW_BATTERY_COUNT, FOB_LOW_DATE_FIRST,
# LAST_PIN_CHANGE and PIN_CHANGE_COUNT. Dates are HHMMSSDDMMYYYY. No secrets.
USER_STATUS_INTS = frozenset(
    {"INVALID_PIN_COUNT", "PIN_CHANGE_COUNT", "FOB_LOW_BATTERY_COUNT"}
)
USER_STATUS_DATES = frozenset({"LAST_PIN_CHANGE", "FOB_LOW_DATE_FIRST"})


def build_user_status_command(user_id: int, username: str, password: str) -> str:
    """Build CMD_GET_USER_STATUS for one user."""
    return _build_command_envelope(
        f'<CMD_GET_USER_STATUS USER_ID="{int(user_id)}" />', username, password
    )


def _spc_date(value: str) -> str | None:
    """HHMMSSDDMMYYYY as ISO 8601 (panel local time); None for unset dates."""
    if len(value) != 14 or not value.isdigit():
        return None
    hh, mi, ss, dd, mo, yyyy = (
        value[0:2],
        value[2:4],
        value[4:6],
        value[6:8],
        value[8:10],
        value[10:14],
    )
    if yyyy in {"0000", "2000"} or dd == "00" or mo == "00":
        return None
    return f"{yyyy}-{mo}-{dd}T{hh}:{mi}:{ss}"


def parse_user_status(response: str) -> dict[str, object]:
    """Return one user's status with snake_case keys and typed values."""
    root = _parse_reply_root(response)
    reply = root.find("REPLY_GET_USER_STATUS")
    if reply is None:
        raise FlexMLError("REPLY_GET_USER_STATUS not found")
    _validate_reply(reply, "REPLY_GET_USER_STATUS")
    element = reply.find("GET_USER_STATUS")
    if element is None:
        element = next(iter(reply), None)
    if element is None:
        raise FlexMLError("GET_USER_STATUS record not found")
    status: dict[str, object] = {}
    for key, raw in element.attrib.items():
        key = key.strip()
        value: object = raw.strip()
        if key in SECRET_FIELDS:
            continue
        if key in USER_STATUS_INTS:
            try:
                value = int(raw)
            except ValueError:
                pass
        elif key in USER_STATUS_DATES:
            value = _spc_date(raw.strip())
        status[key.lower()] = value
    return status


# GET_UNKNOWN_CARDS (checked 2026-11-10): UNKNOWN_CARD records with DOOR_ID,
# CARD_FORMAT, SITE_CODE, CARD_NO, LAST_PRESENTED, PRESENTED_COUNT.
# Card number, format and site code are shown like on the web page (owner
# 2026-11-11); anything that could hold a PIN or code stays masked.
_CARD_SECRET = re.compile(r"(PIN|CODE(?<!SITE_CODE)|DATA|PASS)")


def build_unknown_cards_command(username: str, password: str) -> str:
    """Build CMD_GET_UNKNOWN_CARDS (no attributes)."""
    return _build_command_envelope("<CMD_GET_UNKNOWN_CARDS />", username, password)


def _unknown_card_elements(response: str) -> list[dict[str, str]]:
    """Return the raw unknown-card records, newest first (internal use only)."""
    root = _parse_reply_root(response)
    reply = root.find("REPLY_GET_UNKNOWN_CARDS")
    if reply is None:
        raise FlexMLError("REPLY_GET_UNKNOWN_CARDS not found")
    _validate_reply(reply, "REPLY_GET_UNKNOWN_CARDS")
    elements = [
        dict(element.attrib)
        for element in reply.iter()
        if element is not reply and element.attrib
    ]

    def presented(record: dict[str, str]) -> tuple[str, ...]:
        # LAST_PRESENTED is DD/MM/YYYY HH:MM.
        match = re.match(
            r"(\d{2})/(\d{2})/(\d{4}) (\d{2}):(\d{2})",
            record.get("LAST_PRESENTED", ""),
        )
        return match.group(3, 2, 1, 4, 5) if match else ("",)

    return sorted(elements, key=presented, reverse=True)


def unknown_card_number(response: str, index: int) -> str:
    """Return the card number of unknown card ``index`` (1 = newest)."""
    elements = _unknown_card_elements(response)
    if not 1 <= index <= len(elements):
        raise ValueError(f"There is no unknown card {index} ({len(elements)} known)")
    return check_card_number(elements[index - 1].get("CARD_NO", ""))


def parse_unknown_cards(response: str) -> list[dict[str, str]]:
    """Return the unknown-card records, newest first (PIN-like fields masked).

    ``index`` is what assign_unknown_card takes (1 = newest).
    """
    return [
        {
            key.strip().lower(): (
                "***" if _CARD_SECRET.search(key.upper()) else value.strip()
            )
            for key, value in attrib.items()
        }
        | {"index": str(number)}
        for number, attrib in enumerate(_unknown_card_elements(response), start=1)
    ]
