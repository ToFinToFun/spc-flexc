"""Zone configuration: GET_ZONE_CONFIG / EDIT_ZONE as checked on 2026-11-13."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.spc_flexc.coordinator import SpcFlexCCoordinator
from custom_components.spc_flexc.flexc.flexml import FlexMLError, FlexMLReplyError
from custom_components.spc_flexc.flexc.zone_config import (
    apply_zone_changes,
    build_edit_zone_command,
    parse_edit_zone_reply,
    parse_zone_config,
    zone_attribute_names,
)
from custom_components.spc_flexc.models import SpcState

RECORD = (
    '<FLEXML_REPLY VER="1.0"><REPLY_GET_ZONE_CONFIG RESULT="0" CMD_RESULT="OK">'
    '<ZONES><ZONE ID="40" TYPE="9" NAME="Test zone" ATTRIB="{attrib}" '
    'KEYARM_FUNC="3" AREA="1" TECHDELAY="{delay}" /></ZONES>'
    "</REPLY_GET_ZONE_CONFIG></FLEXML_REPLY>"
)
EMPTY = '<FLEXML_REPLY VER="1.0"></FLEXML_REPLY>'
SAVED = (
    '<FLEXML_REPLY VER="1.0"><REPLY_SAVE_CONFIG RESULT="0" CMD_RESULT="OK">'
    "</REPLY_SAVE_CONFIG></FLEXML_REPLY>"
)


def test_parse_and_names() -> None:
    record = parse_zone_config(RECORD.format(attrib="00000480", delay="49"), 40)
    assert record["TECHDELAY"] == "49"
    assert zone_attribute_names(record["ATTRIB"]) == ["inhibit", "log"]
    with pytest.raises(FlexMLError):
        parse_zone_config(RECORD.format(attrib="00000080", delay="49"), 41)


def test_changes_keep_the_whole_record() -> None:
    record = parse_zone_config(RECORD.format(attrib="00000080", delay="49"), 40)
    updated = apply_zone_changes(
        record, techdelay=50, attributes_on=["log"], attributes_off=["inhibit"]
    )
    assert updated == {
        "ID": "40",
        "TYPE": "9",
        "NAME": "Test zone",
        "ATTRIB": "00000400",
        "KEYARM_FUNC": "3",
        "AREA": "1",
        "TECHDELAY": "50",
    }
    for bad in ({"name": "x" * 17}, {"zone_type": 31}, {"attributes_on": ["nope"]}):
        with pytest.raises(ValueError):
            apply_zone_changes(record, **bad)
    with pytest.raises(ValueError):
        apply_zone_changes(record, attributes_on=["log"], attributes_off=["log"])


def test_edit_command_sends_every_field_and_reply_rules() -> None:
    record = parse_zone_config(RECORD.format(attrib="00000080", delay="49"), 40)
    command = build_edit_zone_command(record, "eng", "pw")
    for field in ('ID="40"', 'TYPE="9"', 'NAME="Test zone"', 'TECHDELAY="49"'):
        assert field in command
    with pytest.raises(ValueError):
        build_edit_zone_command({"ID": "40", "TECHDELAY": "50"}, "eng", "pw")
    parse_edit_zone_reply(EMPTY)  # accepted
    for code in ("17", "65"):
        with pytest.raises(FlexMLReplyError):
            parse_edit_zone_reply(
                f'<FLEXML_REPLY VER="1.0"><REPLY_EDIT_ZONE RESULT="{code}" '
                'CMD_RESULT="ERROR"/></FLEXML_REPLY>'
            )


def _coordinator(replies: list[str], engineer_mode: bool = True) -> MagicMock:
    coordinator = MagicMock(spec=SpcFlexCCoordinator)
    coordinator._client_operation_lock = asyncio.Lock()
    coordinator.client = MagicMock()
    coordinator.client.command_username = "cmd"
    coordinator.client.command_password = "cpw"
    coordinator.client.async_ensure_connected = AsyncMock()
    coordinator.client.async_send_flexml = AsyncMock(side_effect=replies)
    coordinator.state = SpcState()
    coordinator.state.panel.engineer_mode = engineer_mode
    coordinator._engineer = {"username": "eng", "password": "pw", "last_used": 0}
    coordinator.engineer_credentials = MagicMock(return_value=("eng", "pw"))
    coordinator._async_save_config_locked = AsyncMock()
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


@pytest.mark.asyncio
async def test_edit_zone_reads_sends_whole_record_saves_and_checks() -> None:
    before = RECORD.format(attrib="00000080", delay="49")
    after = RECORD.format(attrib="00000080", delay="50")
    coordinator = _coordinator([before, EMPTY, after])
    result = await SpcFlexCCoordinator.async_edit_zone(coordinator, 40, techdelay=50)
    assert result["TECHDELAY"] == "50"
    sent = [c.args[0] for c in coordinator.client.async_send_flexml.call_args_list]
    assert "CMD_EDIT_ZONE" in sent[1] and "eng" in sent[1]
    coordinator._async_save_config_locked.assert_awaited_once()

    # Read back different: reported, never silent.
    coordinator = _coordinator([before, EMPTY, before])
    with pytest.raises(FlexMLError):
        await SpcFlexCCoordinator.async_edit_zone(coordinator, 40, techdelay=50)


@pytest.mark.asyncio
async def test_edit_zone_needs_engineer_and_installer_mode() -> None:
    coordinator = _coordinator([])
    coordinator.engineer_credentials = MagicMock(return_value=None)
    with pytest.raises(FlexMLError):
        await SpcFlexCCoordinator.async_edit_zone(coordinator, 40, techdelay=50)
    coordinator = _coordinator([], engineer_mode=False)
    with pytest.raises(FlexMLError):
        await SpcFlexCCoordinator.async_edit_zone(coordinator, 40, techdelay=50)
    coordinator.client.async_send_flexml.assert_not_called()


@pytest.mark.asyncio
async def test_edit_zone_without_change_sends_nothing() -> None:
    coordinator = _coordinator([RECORD.format(attrib="00000080", delay="49")])
    await SpcFlexCCoordinator.async_edit_zone(coordinator, 40, techdelay=49)
    assert coordinator.client.async_send_flexml.await_count == 1
    coordinator._async_save_config_locked.assert_not_called()


@pytest.mark.asyncio
async def test_edit_zone_name_reloads_the_integration() -> None:
    before = RECORD.format(attrib="00000080", delay="49")
    after = before.replace('NAME="Test zone"', 'NAME="New name"')
    coordinator = _coordinator([before, EMPTY, after])
    coordinator.hass = MagicMock()
    coordinator.entry = MagicMock()
    await SpcFlexCCoordinator.async_edit_zone(coordinator, 40, name="New name")
    coordinator.hass.config_entries.async_schedule_reload.assert_called_once()
