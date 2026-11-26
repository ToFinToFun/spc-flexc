"""One activity log for the panel: what HA sent, what the panel answered,
the events the panel pushed and the panel's own log lines.

Every entry is kept for 30 days (at most 20 000 entries) in Home Assistant's
storage, for the activity card and the ``get_activity`` service, and fired
as a ``spc_flexc_activity`` event, which the logbook shows. Names (users, doors, zones) are shown on purpose: the
owner wants the log to be clear. PINs, card numbers and passwords never are:
commands are reduced to their name and a whitelist of identifying
attributes before anything is kept.
"""

from __future__ import annotations

import re
from collections import deque
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

EVENT_SPC_FLEXC_ACTIVITY = "spc_flexc_activity"

SOURCE_COMMAND = "ha_command"  # HA sent a command to the panel.
SOURCE_REPLY = "panel_reply"  # The panel answered a command.
SOURCE_EVENT = "panel_event"  # The panel pushed an event.
SOURCE_LOG = "panel_log"  # A line from the panel's system or access log.

MAX_ENTRIES = 20_000
KEEP = timedelta(days=30)
SAVE_DELAY = 10

_COMMAND = re.compile(r"<CMD_([A-Z0-9_]+)")
# Attributes shown for a command. Anything else (PIN, CARD_NO, passwords,
# WEBPASS_DATA, rights masks ...) is never kept.
_SHOWN_ATTRIBUTES = (
    "USER_ID",
    "NAME",
    "USER_PROFILE_ID",
    "DOOR_ID",
    "ZONE_ID",
    "AREA_ID",
    "MG_ID",
    "ALERT_ID",
    "ATS_ID",
    "ATP_SEQ_ID",
    "CALENDAR",
    "WEEK",
    "ID",
    "ACTION",
    "MODE",
    "TIME",
)
_ATTRIBUTE = re.compile(r'\b([A-Z][A-Z0-9_]*)="([^"]*)"')
_RESULT = re.compile(
    r'<REPLY_([A-Z0-9_]+)\s+RESULT="(\d+)"(?:\s+CMD_RESULT="([A-Z]+)")?'
)
_READ_PREFIXES = ("GET_", "STATUS_", "READ_", "VERIFY_")


def command_names(command: str) -> list[str]:
    """Return the FlexML command names in one envelope."""
    return list(dict.fromkeys(_COMMAND.findall(command)))


def is_read_only(names: list[str]) -> bool:
    """Reads are polled all the time and are not logged as activity."""
    return bool(names) and all(name.startswith(_READ_PREFIXES) for name in names)


def command_details(command: str) -> dict[str, str]:
    """Return the whitelisted attributes of the first command in an envelope."""
    start = command.find("<CMD_")
    if start < 0:
        return {}
    end = command.find(">", start)
    element = command[start : end if end > 0 else None]
    details = {}
    for key, value in _ATTRIBUTE.findall(element):
        if key in _SHOWN_ATTRIBUTES:
            details[key.lower()] = value
    return details


def reply_result(reply: str) -> tuple[str | None, int | None, str | None]:
    """Return (reply name, RESULT, CMD_RESULT) of the first reply."""
    match = _RESULT.search(reply)
    if match is None:
        return None, None, None
    return match.group(1), int(match.group(2)), match.group(3)


def describe_details(details: dict[str, str]) -> str:
    """Short text for the shown attributes, e.g. 'user 98, name test98'."""
    labels = {
        "user_id": "user",
        "user_profile_id": "profile",
        "door_id": "door",
        "zone_id": "zone",
        "area_id": "area",
        "mg_id": "mapping gate",
        "alert_id": "alert",
        "ats_id": "ATS",
        "atp_seq_id": "ATP",
        "calendar": "calendar",
        "week": "week type",
        "id": "id",
        "action": "action",
        "mode": "mode",
        "time": "time",
        "name": "name",
    }
    return ", ".join(
        f"{labels.get(key, key)} {value}" for key, value in details.items()
    )


class SpcActivityLog:
    """Recent activity of one panel."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self._entries: deque[dict[str, Any]] = deque(maxlen=MAX_ENTRIES)
        self._store: Store[list[dict[str, Any]]] = Store(
            hass, 1, f"spc_flexc.activity.{entry_id}"
        )

    async def async_load(self) -> None:
        """Load the saved entries (best effort) and drop old ones."""
        try:
            saved = await self._store.async_load()
        except Exception:  # noqa: BLE001 - a broken file must not stop setup
            return
        if isinstance(saved, list):
            loaded = [entry for entry in saved if isinstance(entry, dict)]
            self._entries.extend(loaded[-MAX_ENTRIES:])
        self._trim()

    def _trim(self) -> None:
        cutoff = dt_util.now() - KEEP
        while self._entries:
            try:
                first = datetime.fromisoformat(str(self._entries[0].get("time")))
            except ValueError:
                self._entries.popleft()
                continue
            if first >= cutoff:
                break
            self._entries.popleft()

    def _save_data(self) -> list[dict[str, Any]]:
        return list(self._entries)

    def add(
        self,
        source: str,
        title: str,
        message: str,
        *,
        ok: bool | None = None,
        panel_time: str | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        """Keep one entry and fire it as a ``spc_flexc_activity`` event."""
        entry: dict[str, Any] = {
            "time": dt_util.now().isoformat(),
            "panel_time": panel_time,
            "source": source,
            "title": title,
            "message": message,
            "ok": ok,
            **{key: value for key, value in extra.items() if value is not None},
        }
        self._entries.append(entry)
        self._trim()
        self._store.async_delay_save(self._save_data, SAVE_DELAY)
        if source != SOURCE_EVENT:
            # Panel events are already fired (and logged) as spc_flexc_event.
            self.hass.bus.async_fire(
                EVENT_SPC_FLEXC_ACTIVITY, {"entry_id": self.entry_id, **entry}
            )
        return entry

    def recent(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return the newest entries first."""
        return list(reversed(self._entries))[:limit]

    def add_command(self, command: str) -> list[str]:
        """Log a command HA sends; returns its names (empty for reads)."""
        names = command_names(command)
        if not names or is_read_only(names):
            return []
        details = command_details(command)
        text = describe_details(details)
        self.add(
            SOURCE_COMMAND,
            "HA → panel",
            " ".join(names) + (f" ({text})" if text else ""),
            command=",".join(names),
            details=details or None,
        )
        return names

    def add_reply(self, names: list[str], reply: str | None, error: str | None) -> None:
        """Log the panel's answer to a logged command."""
        command = ",".join(names)
        if error is not None:
            self.add(
                SOURCE_REPLY,
                "Panel",
                f"{command}: no answer ({error})",
                ok=False,
                command=command,
            )
            return
        _, result, cmd_result = reply_result(reply or "")
        ok = result == 0
        if ok:
            text = f"{command}: accepted"
        elif result is None:
            text = f"{command}: answer not understood"
        else:
            text = f"{command}: refused (RESULT {result}{', ' + cmd_result if cmd_result else ''})"
        self.add(SOURCE_REPLY, "Panel", text, ok=ok, command=command, result=result)
