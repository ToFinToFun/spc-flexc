"""Panel clock and alert commands: format, reply check, sent once."""

import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import HomeAssistantError

from custom_components.spc_flexc.coordinator import SpcFlexCCoordinator
from custom_components.spc_flexc.flexc.connection import FlexCCommandTimeout
from custom_components.spc_flexc.flexc.flexml import FlexMLError, FlexMLReplyError
from custom_components.spc_flexc.flexc.panel_control import (
    build_clear_all_alerts_command,
    build_set_clock_command,
    parse_simple_reply,
)
from custom_components.spc_flexc.services import PANEL_SCHEMA, _async_panel_command

OK = '<FLEXML_REPLY VER="1.0"><REPLY_{0} RESULT="0" CMD_RESULT="OK"/></FLEXML_REPLY>'


def test_set_clock_command_uses_panel_time_format() -> None:
    command = build_set_clock_command(datetime(2026, 11, 9, 7, 5, 3), "u", "p")
    assert '<CMD_SET_CLOCK TIME="07050309112026" />' in command


def test_clear_all_alerts_command() -> None:
    assert "<CMD_CLEAR_ALL_ALERTS />" in build_clear_all_alerts_command("u", "p")


def test_parse_simple_reply() -> None:
    parse_simple_reply(OK.format("SET_CLOCK"), "SET_CLOCK")
    with pytest.raises(FlexMLError):
        parse_simple_reply(OK.format("SET_CLOCK"), "CLEAR_ALL_ALERTS")
    with pytest.raises(FlexMLReplyError):
        parse_simple_reply(
            '<FLEXML_REPLY VER="1.0"><REPLY_SET_CLOCK RESULT="54" '
            'CMD_RESULT="ERROR"/></FLEXML_REPLY>',
            "SET_CLOCK",
        )


def _coordinator(reply: str | Exception) -> MagicMock:
    import asyncio

    coordinator = MagicMock(spec=SpcFlexCCoordinator)
    coordinator._client_operation_lock = asyncio.Lock()
    coordinator.client = MagicMock()
    coordinator.client.async_ensure_connected = AsyncMock()
    if isinstance(reply, Exception):
        coordinator.client.async_send_flexml = AsyncMock(side_effect=reply)
    else:
        coordinator.client.async_send_flexml = AsyncMock(return_value=reply)
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "command"),
    [
        (SpcFlexCCoordinator.async_set_panel_clock, "SET_CLOCK"),
        (SpcFlexCCoordinator.async_clear_all_alerts, "CLEAR_ALL_ALERTS"),
    ],
)
async def test_panel_commands_are_sent_once(method, command) -> None:
    coordinator = _coordinator(OK.format(command))
    await method(coordinator)
    coordinator.client.async_send_flexml.assert_awaited_once()
    assert f"<CMD_{command}" in coordinator.client.async_send_flexml.call_args.args[0]
    coordinator.async_request_refresh.assert_awaited_once()

    failing = _coordinator(FlexCCommandTimeout("lost"))
    with pytest.raises(FlexCCommandTimeout):
        await method(failing)
    failing.client.async_send_flexml.assert_awaited_once()


@pytest.mark.asyncio
async def test_panel_command_service_reports_errors() -> None:
    coordinator = MagicMock()
    coordinator.async_clear_all_alerts = AsyncMock(side_effect=FlexCCommandTimeout("x"))
    entry = MagicMock(
        entry_id="abc", state=ConfigEntryState.LOADED, runtime_data=coordinator
    )
    hass = MagicMock()
    hass.config_entries.async_entries.return_value = [entry]
    call = MagicMock(data=PANEL_SCHEMA({}), service="clear_alerts")
    with pytest.raises(HomeAssistantError):
        await _async_panel_command(hass, call, "async_clear_all_alerts")


def test_engineer_mode_commands() -> None:
    from custom_components.spc_flexc.flexc.panel_control import (
        build_engineer_mode_command,
    )

    enter = build_engineer_mode_command(True, "eng", "secret")
    assert "<CMD_ENTER_FULL_ENGINEER_MODE />" in enter
    assert 'PANEL_USERNAME="eng"' in enter
    assert "<CMD_EXIT_FULL_ENGINEER_MODE />" in build_engineer_mode_command(
        False, "eng", "secret"
    )


def _engineer_coordinator(reply: str, data: dict | None = None) -> MagicMock:
    from custom_components.spc_flexc.models import SpcState

    coordinator = _coordinator(reply)
    coordinator.entry = MagicMock()
    coordinator.entry.data = dict(data or {})
    coordinator.state = SpcState()
    coordinator.hass = MagicMock()
    coordinator._engineer = None
    coordinator.engineer_credentials = lambda: SpcFlexCCoordinator.engineer_credentials(
        coordinator
    )
    coordinator._store_engineer_login = lambda u, p: (
        SpcFlexCCoordinator._store_engineer_login(coordinator, u, p)
    )
    coordinator.hass.data = {}
    coordinator._engineer_sessions = lambda: SpcFlexCCoordinator._engineer_sessions(
        coordinator
    )
    coordinator._keep_engineer_session = lambda: (
        SpcFlexCCoordinator._keep_engineer_session(coordinator)
    )
    return coordinator


VERIFY = (
    '<FLEXML_REPLY VER="1.0"><REPLY_VERIFY_USER_ON_PANEL RESULT="0" CMD_RESULT="OK">'
    '<VERIFY_USER USER_ID="{0}" ENGINEER="{1}" REMOTE_ACCESS="1"/>'
    "</REPLY_VERIFY_USER_ON_PANEL></FLEXML_REPLY>"
)


@pytest.mark.asyncio
async def test_engineer_mode_uses_engineer_login_once() -> None:
    coordinator = _engineer_coordinator(OK.format("ENTER_FULL_ENGINEER_MODE"))
    coordinator._engineer = {
        "username": "eng",
        "password": "pw",
        "remember": False,
        "user_id": 9999,
        "last_used": time.monotonic(),
    }
    await SpcFlexCCoordinator.async_set_engineer_mode(coordinator, True)
    sent = coordinator.client.async_send_flexml.call_args.args[0]
    assert 'PANEL_USERNAME="eng"' in sent
    coordinator.client.async_send_flexml.assert_awaited_once()


@pytest.mark.asyncio
async def test_engineer_mode_needs_login() -> None:
    coordinator = _engineer_coordinator(OK.format("EXIT_FULL_ENGINEER_MODE"))
    with pytest.raises(FlexMLError):
        await SpcFlexCCoordinator.async_set_engineer_mode(coordinator, False)
    coordinator.client.async_send_flexml.assert_not_awaited()


def test_engineer_login_ends_when_idle_but_not_in_engineer_mode() -> None:
    coordinator = _engineer_coordinator("")
    coordinator._engineer = {
        "username": "eng",
        "password": "pw",
        "remember": False,
        "user_id": 9999,
        "last_used": time.monotonic() - 4000,
    }
    coordinator.state.panel.engineer_mode = True
    assert SpcFlexCCoordinator.engineer_credentials(coordinator) == ("eng", "pw")
    coordinator.state.panel.engineer_mode = False
    assert SpcFlexCCoordinator.engineer_credentials(coordinator) is None
    coordinator._engineer = {
        "username": "eng",
        "password": "pw",
        "remember": True,
        "user_id": 9999,
        "last_used": time.monotonic() - 4000,
    }
    assert SpcFlexCCoordinator.engineer_credentials(coordinator) == ("eng", "pw")


@pytest.mark.asyncio
async def test_engineer_login_checks_the_panel_and_remembers_only_on_request() -> None:
    coordinator = _engineer_coordinator(VERIFY.format("9999", "1"))
    await SpcFlexCCoordinator.async_engineer_login(coordinator, "eng", "pw", False)
    assert (
        "<CMD_VERIFY_USER_ON_PANEL />"
        in coordinator.client.async_send_flexml.call_args.args[0]
    )
    assert coordinator._engineer["user_id"] == 9999
    coordinator.hass.config_entries.async_update_entry.assert_not_called()

    await SpcFlexCCoordinator.async_engineer_login(coordinator, "eng", "pw", True)
    data = coordinator.hass.config_entries.async_update_entry.call_args.kwargs["data"]
    assert data == {"engineer_username": "eng", "engineer_password": "pw"}


@pytest.mark.asyncio
async def test_engineer_login_refuses_a_non_engineer() -> None:
    coordinator = _engineer_coordinator(VERIFY.format("9995", "0"))
    with pytest.raises(FlexMLError):
        await SpcFlexCCoordinator.async_engineer_login(coordinator, "u", "p", True)
    assert coordinator._engineer is None
    coordinator.hass.config_entries.async_update_entry.assert_not_called()


@pytest.mark.asyncio
async def test_engineer_logout_forgets_and_waits_for_engineer_mode_off() -> None:
    coordinator = _engineer_coordinator(
        "", {"engineer_username": "eng", "engineer_password": "pw", "host": "x"}
    )
    coordinator._engineer = {
        "username": "eng",
        "password": "pw",
        "remember": True,
        "user_id": 9999,
        "last_used": time.monotonic(),
    }
    coordinator.state.panel.engineer_mode = True
    with pytest.raises(FlexMLError):
        await SpcFlexCCoordinator.async_engineer_logout(coordinator)
    coordinator.state.panel.engineer_mode = False
    await SpcFlexCCoordinator.async_engineer_logout(coordinator)
    assert coordinator._engineer is None
    data = coordinator.hass.config_entries.async_update_entry.call_args.kwargs["data"]
    assert data == {"host": "x"}


def test_engineer_switch_state() -> None:
    from custom_components.spc_flexc.models import SpcState
    from custom_components.spc_flexc.switch import SpcEngineerModeSwitch

    coordinator = MagicMock()
    coordinator.entry.entry_id = "test"
    coordinator.data = SpcState()
    switch = SpcEngineerModeSwitch(coordinator)
    assert switch.is_on is None
    coordinator.data.panel.engineer_mode = True
    assert switch.is_on is True


def test_engineer_login_is_stored_only_when_complete() -> None:
    from custom_components.spc_flexc.config_flow import _without_empty_engineer_login

    base = {"host": "192.0.2.1"}
    assert (
        _without_empty_engineer_login(
            {**base, "engineer_username": "eng", "engineer_password": ""}
        )
        == base
    )
    full = {**base, "engineer_username": "eng", "engineer_password": "pw"}
    assert _without_empty_engineer_login(full) == full


def test_untested_command_formats() -> None:
    from custom_components.spc_flexc.flexc.panel_control import (
        build_alert_control_command,
        build_flexc_manual_test_command,
        build_silence_all_bells_command,
    )

    assert "<CMD_SILENCE_ALL_BELLS />" in build_silence_all_bells_command("u", "p")
    assert (
        '<CMD_REQUEST_FLEXC_MANUAL_TEST ATS_ID="2" ATP_SEQ_ID="1" />'
        in build_flexc_manual_test_command(2, 1, "u", "p")
    )
    assert (
        '<CMD_ALERT_CONTROL ALERT_ID="38" ACTION="2" />'
        in build_alert_control_command(38, 2, "u", "p")
    )
    with pytest.raises(ValueError):
        build_alert_control_command(38, 4, "u", "p")


def _alert_coordinator(reply: str, isolated_after: bool) -> MagicMock:
    from custom_components.spc_flexc.flexc.panel_status import SystemAlertState
    from custom_components.spc_flexc.models import SpcState

    coordinator = _coordinator(reply)
    coordinator.client.command_username = "u"
    coordinator.client.command_password = "p"
    coordinator.state = SpcState()

    async def read_status() -> None:
        coordinator.state.system_alerts = {
            "network_fault": SystemAlertState(
                active=False,
                alerted=False,
                inhibited=False,
                isolated=isolated_after,
                inhibit_allowed=True,
                isolate_allowed=True,
            )
        }

    coordinator._async_read_panel_status_locked = read_status
    return coordinator


@pytest.mark.asyncio
async def test_alert_control_checks_the_panel_status() -> None:
    ok = _alert_coordinator(OK.format("ALERT_CONTROL"), isolated_after=True)
    await SpcFlexCCoordinator.async_alert_control(ok, "network_fault", 2)
    ok.client.async_send_flexml.assert_awaited_once()
    # ALERT_ID is the SYSALERT bit (24 for the network fault), not 38.
    assert 'ALERT_ID="24" ACTION="2"' in ok.client.async_send_flexml.call_args.args[0]

    unchanged = _alert_coordinator(OK.format("ALERT_CONTROL"), isolated_after=False)
    with pytest.raises(FlexMLError):
        await SpcFlexCCoordinator.async_alert_control(unchanged, "network_fault", 2)

    with pytest.raises(ValueError):
        await SpcFlexCCoordinator.async_alert_control(ok, "no_such_alert", 2)


@pytest.mark.asyncio
async def test_silence_and_test_call_are_sent_once() -> None:
    silence = _coordinator(OK.format("SILENCE_ALL_BELLS"))
    silence._async_send_panel_command = lambda command, name: (
        SpcFlexCCoordinator._async_send_panel_command(silence, command, name)
    )
    await SpcFlexCCoordinator.async_silence_bells(silence)
    silence.client.async_send_flexml.assert_awaited_once()

    test_call = _coordinator(OK.format("REQUEST_FLEXC_MANUAL_TEST"))
    test_call._async_send_panel_command = lambda command, name: (
        SpcFlexCCoordinator._async_send_panel_command(test_call, command, name)
    )
    await SpcFlexCCoordinator.async_request_flexc_test(test_call, 2, 1)
    assert 'ATP_SEQ_ID="1"' in test_call.client.async_send_flexml.call_args.args[0]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kind", "on", "action"),
    [
        ("inhibit", True, 0),
        ("inhibit", False, 1),
        ("isolate", True, 2),
        ("isolate", False, 3),
    ],
)
async def test_system_alert_switch_actions(kind, on, action) -> None:
    from custom_components.spc_flexc.models import SpcState
    from custom_components.spc_flexc.switch import SpcSystemAlertControlSwitch

    coordinator = MagicMock()
    coordinator.entry.entry_id = "test"
    coordinator.data = SpcState()
    coordinator.async_alert_control = AsyncMock()
    switch = SpcSystemAlertControlSwitch(coordinator, "network_fault", kind)
    assert switch.entity_registry_enabled_default is True
    await (switch.async_turn_on() if on else switch.async_turn_off())
    coordinator.async_alert_control.assert_awaited_once_with("network_fault", action)


@pytest.mark.asyncio
async def test_engineer_login_survives_a_reload_in_memory() -> None:
    """Not remembered: kept in hass.data for a reload, gone at logout."""
    coordinator = _engineer_coordinator(VERIFY.format("9999", "1"))
    await SpcFlexCCoordinator.async_engineer_login(coordinator, "eng", "pw", False)
    sessions = coordinator.hass.data["spc_flexc_engineer_sessions"]
    assert sessions[coordinator.entry.entry_id]["username"] == "eng"
    assert "spc_flexc_engineer_username" not in coordinator.entry.data
    await SpcFlexCCoordinator.async_engineer_logout(coordinator)
    assert coordinator.entry.entry_id not in sessions
