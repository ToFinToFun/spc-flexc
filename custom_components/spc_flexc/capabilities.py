"""What the integration can do on this panel, function by function.

Each function has a fixed status from the work on the reference panel
(``docs/FLEXC_PROTOCOL.md``, *Command catalogue*) and, once the panel has
answered one of its commands, the live result. The Capabilities sensor shows
both, so it is clear what works, what is untested, what the command profile
does not allow and what needs an engineer login.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Fixed status of a function.
WORKS = "works"  # Checked on a panel.
UNTESTED = "untested"  # Built from a qualified guess, not run on a panel.
NOT_BUILT = "not_built"  # The panel has the command; the integration not.
NO_HARDWARE = "no_hardware"  # Needs hardware the reference panel lacks.

# Live status, from the panel's answers.
REFUSED = "refused"  # The panel answered with an error (see result).
NEEDS_ENGINEER = "needs_engineer"  # Needs an engineer login that is not set.


@dataclass(frozen=True)
class Capability:
    """One function of the integration."""

    key: str
    group: str
    commands: tuple[str, ...]
    status: str
    engineer: bool = False


CAPABILITIES: tuple[Capability, ...] = (
    # Panel and system
    Capability("panel_status", "system", ("GET_PANEL_SUMMARY", "STATUS_PANEL"), WORKS),
    Capability("panel_settings", "system", ("READ_INTRUDER_CFG",), WORKS),
    Capability("set_clock", "system", ("SET_CLOCK",), WORKS),
    Capability("save_config", "system", ("SAVE_CONFIG",), WORKS),
    Capability(
        "engineer_mode",
        "system",
        ("ENTER_FULL_ENGINEER_MODE", "EXIT_FULL_ENGINEER_MODE"),
        WORKS,
        engineer=True,
    ),
    Capability(
        "engineer_access",
        "system",
        ("GRANT_ENGINEER_ACCESS", "REVOKE_ENGINEER_ACCESS"),
        NOT_BUILT,
    ),
    Capability("xbus", "system", ("STATUS_XBUS",), WORKS),
    Capability("logs", "system", ("GET_SYSTEM_LOG", "GET_ZONE_LOG"), WORKS),
    # Intruder alarm
    Capability("areas", "alarm", ("GET_AREA_STATUS", "AREA_CHANGE_MODE"), WORKS),
    Capability("zones", "alarm", ("GET_ZONE_STATUS", "ZONE_CONTROL"), WORKS),
    Capability("alerts", "alarm", ("GET_ALERT_STATUS", "CLEAR_ALL_ALERTS"), WORKS),
    Capability("alert_control", "alarm", ("ALERT_CONTROL",), WORKS),
    Capability("silence_bells", "alarm", ("SILENCE_ALL_BELLS",), WORKS),
    Capability(
        "holdup", "alarm", ("GET_HOLDUP_CONFIG", "EDIT_HOLDUP_CONFIG"), NOT_BUILT
    ),
    Capability("zone_config", "alarm", ("EDIT_ZONE",), WORKS, engineer=True),
    Capability("virtual_keypad", "alarm", ("VIRTUAL_KEYPAD_CONTROL",), NOT_BUILT),
    Capability("wireless", "alarm", ("GET_WIRELESS_LOG",), WORKS),
    # Outputs
    Capability("mapping_gates", "outputs", ("GET_MG_STATUS", "MG_CONTROL"), WORKS),
    # Access control
    Capability(
        "doors",
        "access",
        ("GET_DOOR_CONFIG", "GET_DOOR_STATUS", "DOOR_CONTROL"),
        WORKS,
    ),
    Capability("access_log", "access", ("GET_ACCESS_LOG",), WORKS),
    Capability("unknown_cards", "access", ("GET_UNKNOWN_CARDS",), WORKS),
    # Users and codes
    Capability("users", "users", ("GET_USER_CONFIG", "EDIT_USER"), WORKS),
    Capability("add_delete_users", "users", ("ADD_USER", "DELETE_USER"), WORKS),
    Capability("pins", "users", ("EDIT_USER",), WORKS),
    Capability("user_status", "users", ("GET_USER_STATUS",), WORKS),
    Capability(
        "user_profiles",
        "users",
        (
            "GET_USER_PROFILE_CONFIG",
            "ADD_USER_PROFILE",
            "EDIT_USER_PROFILE",
            "DELETE_USER_PROFILE",
        ),
        WORKS,
    ),
    Capability(
        "user_devices",
        "users",
        ("ADD_USER_PACE", "ADD_USER_FOB", "ADD_USER_SMS", "ADD_USER_TWW_TAG"),
        NO_HARDWARE,
    ),
    # Calendars
    Capability(
        "calendars",
        "calendars",
        (
            "GET_CALENDAR_CONFIG",
            "EDIT_CALENDAR",
            "EDIT_CALENDAR_WEEK",
            "ADD_CALENDAR",
            "DELETE_CALENDAR",
        ),
        WORKS,
    ),
    Capability(
        "calendar_exceptions",
        "calendars",
        ("ADD_CALEX", "EDIT_CALEX", "DELETE_CALEX"),
        WORKS,
    ),
    # FlexC and communication
    Capability("flexc_status", "communication", ("GET_FLEXC_ATS_STATUS",), WORKS),
    Capability(
        "flexc_logs",
        "communication",
        (
            "GET_FLEXC_ATS_EVENT_LOG",
            "GET_FLEXC_ATS_NETWORK_LOG",
            "GET_FLEXC_ATP_LOG",
            "GET_FLEXC_ATP_NETWORK_LOG",
        ),
        WORKS,
    ),
    Capability(
        "flexc_test_call", "communication", ("REQUEST_FLEXC_MANUAL_TEST",), WORKS
    ),
    Capability(
        "modem", "communication", ("GET_MODEM_STATUS", "GET_MODEM_LOG"), NO_HARDWARE
    ),
    Capability("camera", "communication", ("GET_CAMERA_IMAGE",), NO_HARDWARE),
    Capability(
        "flexc_admin",
        "communication",
        ("DELETE_FLEXC_ATS", "DELETE_FLEXC_ATP", "REQUEST_FLEXC_UPDATE_ENCKEY"),
        NOT_BUILT,
    ),
    Capability(
        "files_firmware",
        "communication",
        ("UPLOAD_FILE", "DOWNLOAD_FILE", "UPGRADE_PANEL_FIRMWARE", "RESET_PANEL"),
        NOT_BUILT,
    ),
)


def capability_report(
    results: dict[str, dict[str, Any]], has_engineer_login: bool
) -> list[dict[str, Any]]:
    """Return every function with its fixed and live status.

    ``results`` maps a command name to its last answer:
    ``{"result": int | None, "time": iso}``.
    """
    report = []
    for capability in CAPABILITIES:
        seen = {name: results[name] for name in capability.commands if name in results}
        refused = {
            name: answer["result"]
            for name, answer in seen.items()
            if answer.get("result") not in (0, None)
        }
        status = capability.status
        if capability.engineer and not has_engineer_login:
            status = NEEDS_ENGINEER
        if refused:
            status = REFUSED
        entry: dict[str, Any] = {
            "function": capability.key,
            "group": capability.group,
            "status": status,
            "commands": list(capability.commands),
        }
        if seen:
            entry["last_used"] = max(str(a.get("time")) for a in seen.values())
        if refused:
            entry["refused"] = refused
        report.append(entry)
    return report
