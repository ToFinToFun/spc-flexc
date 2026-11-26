"""Activity log: commands, answers and log lines, never PINs or card numbers."""

from unittest.mock import MagicMock

from custom_components.spc_flexc.activity import (
    EVENT_SPC_FLEXC_ACTIVITY,
    SOURCE_COMMAND,
    SOURCE_EVENT,
    SOURCE_REPLY,
    SpcActivityLog,
    command_details,
    is_read_only,
    reply_result,
)

EDIT = (
    '<FLEXML_CMD VER="1.0" PANEL_USERNAME="u" PANEL_PASSWORD="secret">'
    '<CMD_EDIT_USER USER_ID="98" NAME="test98" PIN="5A5A1234" CARD_NO="12345" '
    'WEBPASS_DATA="web" /></FLEXML_CMD>'
)


def _log() -> tuple[SpcActivityLog, MagicMock]:
    hass = MagicMock()
    log = SpcActivityLog(hass, "entry")
    log._store = MagicMock()
    return log, hass


def test_command_details_never_keep_secrets() -> None:
    details = command_details(EDIT)
    assert details == {"user_id": "98", "name": "test98"}


def test_reads_are_not_logged() -> None:
    log, hass = _log()
    assert is_read_only(["GET_USER_CONFIG"])
    assert log.add_command("<FLEXML_CMD><CMD_GET_SYSTEM_LOG /></FLEXML_CMD>") == []
    assert log.recent() == []
    hass.bus.async_fire.assert_not_called()


def test_command_and_answer_are_logged() -> None:
    log, hass = _log()
    names = log.add_command(EDIT)
    log.add_reply(
        names,
        '<FLEXML_REPLY VER="1.0"><REPLY_EDIT_USER RESULT="0" CMD_RESULT="OK"/></FLEXML_REPLY>',
        None,
    )
    log.add_reply(
        names,
        '<FLEXML_REPLY VER="1.0"><REPLY_EDIT_USER RESULT="59" CMD_RESULT="ERROR"/></FLEXML_REPLY>',
        None,
    )
    refused, accepted, sent = log.recent()
    assert sent["source"] == SOURCE_COMMAND
    assert sent["message"] == "EDIT_USER (user 98, name test98)"
    assert accepted["source"] == SOURCE_REPLY and accepted["ok"] is True
    assert refused["ok"] is False and refused["result"] == 59
    everything = repr(log.recent()) + repr(hass.bus.async_fire.call_args_list)
    for secret in ("5A5A1234", "12345", "secret", "web"):
        assert secret not in everything
    assert hass.bus.async_fire.call_args.args[0] == EVENT_SPC_FLEXC_ACTIVITY


def test_panel_events_are_kept_but_not_fired_again() -> None:
    log, hass = _log()
    log.add(SOURCE_EVENT, "Entredörr", "Entry granted")
    assert log.recent()[0]["message"] == "Entry granted"
    hass.bus.async_fire.assert_not_called()


def test_reply_result() -> None:
    assert reply_result('<REPLY_SAVE_CONFIG RESULT="0" CMD_RESULT="OK">') == (
        "SAVE_CONFIG",
        0,
        "OK",
    )


def test_old_entries_are_dropped() -> None:
    log, _ = _log()
    log._entries.append({"time": "2000-01-01T00:00:00+00:00", "message": "old"})
    log.add(SOURCE_REPLY, "Panel", "new")
    assert [e["message"] for e in log.recent()] == ["new"]
    log._store.async_delay_save.assert_called()


def test_capability_report_marks_refusals_and_engineer() -> None:
    from custom_components.spc_flexc.capabilities import (
        NEEDS_ENGINEER,
        REFUSED,
        WORKS,
        capability_report,
    )

    report = {
        e["function"]: e
        for e in capability_report(
            {
                "GET_USER_CONFIG": {"result": 0, "time": "t1"},
                "ADD_USER": {"result": 59, "time": "t2"},
            },
            has_engineer_login=False,
        )
    }
    assert report["users"]["status"] == WORKS
    assert report["users"]["last_used"] == "t1"
    assert report["add_delete_users"]["status"] == REFUSED
    assert report["add_delete_users"]["refused"] == {"ADD_USER": 59}
    assert report["engineer_mode"]["status"] == NEEDS_ENGINEER
