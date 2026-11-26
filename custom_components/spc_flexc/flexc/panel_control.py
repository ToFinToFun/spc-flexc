"""State-changing panel commands that are not tied to one area, zone or door.

These are sent once. They are never retried automatically, because the panel
may have applied a command whose reply was lost.
"""

from __future__ import annotations

from datetime import datetime

from .flexml import (
    FlexMLError,
    FlexMLReplyError,
    _build_command_envelope,
    _parse_reply_root,
    _validate_reply,
)

PANEL_TIME_FORMAT = "%H%M%S%d%m%Y"


def build_set_clock_command(local_time: datetime, username: str, password: str) -> str:
    """Build CMD_SET_CLOCK for the given local wall-clock time."""
    return _build_command_envelope(
        f'<CMD_SET_CLOCK TIME="{local_time.strftime(PANEL_TIME_FORMAT)}" />',
        username,
        password,
    )


def build_clear_all_alerts_command(username: str, password: str) -> str:
    """Build CMD_CLEAR_ALL_ALERTS."""
    return _build_command_envelope("<CMD_CLEAR_ALL_ALERTS />", username, password)


def build_engineer_mode_command(enter: bool, username: str, password: str) -> str:
    """Build CMD_ENTER_FULL_ENGINEER_MODE or CMD_EXIT_FULL_ENGINEER_MODE.

    The panel accepts these only from an engineer login (RESULT 52 otherwise).
    """
    command = "ENTER_FULL_ENGINEER_MODE" if enter else "EXIT_FULL_ENGINEER_MODE"
    return _build_command_envelope(f"<CMD_{command} />", username, password)


def build_verify_user_command(username: str, password: str) -> str:
    """Build CMD_VERIFY_USER_ON_PANEL: the panel says who the login is."""
    return _build_command_envelope("<CMD_VERIFY_USER_ON_PANEL />", username, password)


def parse_verify_user(response: str) -> dict[str, object]:
    """Read the VERIFY_USER answer: user ID, engineer and remote access.

    Seen on the panel: <VERIFY_USER USER_ID="9995" ENGINEER="0"
    REMOTE_ACCESS="1"/>. A refused login answers a non-zero RESULT.
    """
    root = _parse_reply_root(response)
    reply = root.find("REPLY_VERIFY_USER_ON_PANEL")
    if reply is not None and reply.get("RESULT") not in (None, "0"):
        raise FlexMLReplyError(
            f"REPLY_VERIFY_USER_ON_PANEL failed: RESULT={reply.get('RESULT')!r}"
        )
    element = root.find(".//VERIFY_USER")
    if element is None:
        raise FlexMLError("VERIFY_USER not found")
    user_id = element.get("USER_ID")
    return {
        "user_id": int(user_id) if user_id and user_id.isdigit() else None,
        "engineer": element.get("ENGINEER") == "1",
        "remote_access": element.get("REMOTE_ACCESS") == "1",
    }


def build_save_config_command(username: str, password: str) -> str:
    """Build CMD_SAVE_CONFIG, sent without attributes.

    A FlexC configuration change (EDIT_USER, EDIT_CALENDAR ...) is only held
    in the panel's memory. Without a save the panel's checksum check fails
    and it restarts with the last saved configuration (seen on an SPC4300,
    3.14.1). The web interface saves after every change.
    """
    return _build_command_envelope("<CMD_SAVE_CONFIG />", username, password)


def build_silence_all_bells_command(username: str, password: str) -> str:
    """Build CMD_SILENCE_ALL_BELLS. UNTESTED: sent without attributes."""
    return _build_command_envelope("<CMD_SILENCE_ALL_BELLS />", username, password)


def build_flexc_manual_test_command(
    ats_id: int, atp_seq_id: int, username: str, password: str
) -> str:
    """Build CMD_REQUEST_FLEXC_MANUAL_TEST. UNTESTED.

    The attributes are those that GET_FLEXC_ATP_LOG accepts (verified).
    """
    return _build_command_envelope(
        f'<CMD_REQUEST_FLEXC_MANUAL_TEST ATS_ID="{int(ats_id)}" '
        f'ATP_SEQ_ID="{int(atp_seq_id)}" />',
        username,
        password,
    )


# ALERT_CONTROL actions. UNTESTED: assumed to match CMD_ZONE_CONTROL.
ALERT_ACTION_INHIBIT = 0
ALERT_ACTION_DEINHIBIT = 1
ALERT_ACTION_ISOLATE = 2
ALERT_ACTION_DEISOLATE = 3


def build_alert_control_command(
    alert_id: int, action: int, username: str, password: str
) -> str:
    """Build CMD_ALERT_CONTROL. UNTESTED: ALERT_ID and ACTION are a guess."""
    if action not in (0, 1, 2, 3):
        raise ValueError("Alert action must be 0-3")
    return _build_command_envelope(
        f'<CMD_ALERT_CONTROL ALERT_ID="{int(alert_id)}" ACTION="{action}" />',
        username,
        password,
    )


def parse_simple_reply(response: str, command: str) -> None:
    """Validate the reply of a command that returns no data."""
    reply_tag = f"REPLY_{command}"
    root = _parse_reply_root(response)
    reply = root.find(reply_tag)
    if reply is None:
        raise FlexMLError(f"{reply_tag} not found")
    _validate_reply(reply, reply_tag)
