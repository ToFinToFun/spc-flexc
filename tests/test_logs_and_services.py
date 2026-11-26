"""Panel logs, the get_log service and Mapping Gate events."""

from datetime import UTC
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from custom_components.spc_flexc.bus_events import build_event_data
from custom_components.spc_flexc.flexc.connection import FlexCCommandTimeout
from custom_components.spc_flexc.flexc.flexml import FlexMLError, FlexMLReplyError
from custom_components.spc_flexc.flexc.logs import build_log_command, parse_log
from custom_components.spc_flexc.mapping_gate_coordinator import (
    SpcFlexCMappingGateCoordinator,
)
from custom_components.spc_flexc.models import MappingGateState, SpcState
from custom_components.spc_flexc.services import GET_LOG_SCHEMA, _async_get_log

# Record shapes as sent by an SPC4300 (firmware 3.16); values are placeholders.
ACCESS_LOG = (
    '<FLEXML_REPLY VER="1.0"><REPLY_GET_ACCESS_LOG RESULT="0" CMD_RESULT="OK">'
    '<ACCESS_LOG_EVENT TIME="15411820102026" TYPE="5" DOOR_ID="3" '
    'DOOR_NAME="Front door" LOG_TEXT="Exit button"  />'
    '<ACCESS_LOG_EVENT TIME="19270622102026" TYPE="1" DOOR_ID="3" '
    'DOOR_NAME="Front door" USER_ID="4" USER_NAME="Guest" '
    'LOG_TEXT="Entry granted (Guest)"  />'
    '<ACCESS_LOG_EVENT TIME="19300022102026" TYPE="2" DETAIL="4" DOOR_ID="3" '
    'DOOR_NAME="Front door" LOG_TEXT="Denied"  />'
    "</REPLY_GET_ACCESS_LOG></FLEXML_REPLY>"
)
ATS_LOG = (
    '<FLEXML_REPLY VER="1.0"><REPLY_GET_FLEXC_ATS_EVENT_LOG RESULT="0" CMD_RESULT="OK">'
    '<ATS_EVENT_LOG EV_SEQ="561" EV_GRP="18" EV_ID="3014" EV_DESC="Unknown card" '
    'TIMESTAMP="16184209112026" SIA_CODE="DD" SIA_ADDRESS="3" DOOR_ID="3" '
    'DOOR_NAME="Front door" AREA_ID="1" AREA_NAME="House" CARD_FORMAT="11" '
    'CARD_BIT_COUNT="6" CARD_NUM="123456" />'
    '<ATS_EVENT_LOG EV_SEQ="562" EV_GRP="12" EV_ID="7014" EV_DESC="Gate off" '
    'TIMESTAMP="16190009112026" MG_ID="2" MG_NAME="Boiler" />'
    "</REPLY_GET_FLEXC_ATS_EVENT_LOG></FLEXML_REPLY>"
)
SYSTEM_LOG = (
    '<FLEXML_REPLY VER="1.0"><REPLY_GET_SYSTEM_LOG RESULT="0" CMD_RESULT="OK">'
    '<SYSTEM_LOG_EVENT TIME="23250703112026" RAW="076F020000000000" TEXT="Config changed" />'
    "</REPLY_GET_SYSTEM_LOG></FLEXML_REPLY>"
)
ZONE_LOG = (
    '<FLEXML_REPLY VER="1.0"><REPLY_GET_ZONE_LOG RESULT="0" CMD_RESULT="OK">'
    '<ZONE_LOG_EVENT TIME="09573506112026" ZONE_ID="25" INPUT="1" RESISTANCE="255" />'
    '<ZONE_LOG_EVENT TIME="09573606112026" ZONE_ID="25" INPUT="0" RESISTANCE="0" />'
    "</REPLY_GET_ZONE_LOG></FLEXML_REPLY>"
)


def test_build_log_commands() -> None:
    assert '<CMD_GET_ACCESS_LOG DOOR_ID="3" />' in build_log_command(
        "access", 3, "u", "p"
    )
    assert "<CMD_GET_SYSTEM_LOG />" in build_log_command("system", None, "u", "p")
    assert '<CMD_GET_FLEXC_ATS_EVENT_LOG ATS_ID="2" />' in build_log_command(
        "ats", 2, "u", "p"
    )
    with pytest.raises(ValueError):
        build_log_command("zone", None, "u", "p")


def test_access_log_newest_first_with_type_names() -> None:
    records = parse_log(ACCESS_LOG, "access", UTC)
    assert [r["type"] for r in records] == [2, 1, 5]
    assert records[0]["type_name"] == "denied"
    assert records[0]["detail"] == 4
    assert records[1]["user_name"] == "Guest"
    assert records[2]["type_name"] == "door_release"
    assert records[2]["time"] == "2026-10-20T15:41:18+00:00"


def test_ats_log_never_returns_card_data() -> None:
    records = parse_log(ATS_LOG, "ats", UTC)
    assert records[0]["event_id"] == 7014
    assert records[0]["mapping_gate_name"] == "Boiler"
    unknown_card = records[1]
    assert unknown_card["event_id"] == 3014
    assert not any("card" in key for key in unknown_card)
    assert "123456" not in str(records)


def test_event_bus_data_never_contains_card_data() -> None:
    event = {"EV_ID": "3014", "DOOR_ID": "3", "CARD_NUM": "123456", "CARD_FORMAT": "11"}
    data = build_event_data("entry", event, "Unknown card", UTC)
    assert "123456" not in str(data)
    assert not any("card" in key for key in data)


def test_system_and_zone_logs() -> None:
    assert parse_log(SYSTEM_LOG, "system", UTC) == [
        {
            "time": "2026-11-03T23:25:07+00:00",
            "text": "Config changed",
            "raw": "076F020000000000",
        }
    ]
    zone = parse_log(ZONE_LOG, "zone", UTC)
    assert [(r["input"], r["resistance"]) for r in zone] == [(0, 0), (1, 255)]


def test_log_errors() -> None:
    with pytest.raises(FlexMLError):
        parse_log(SYSTEM_LOG, "access", UTC)
    with pytest.raises(FlexMLReplyError):
        parse_log(
            '<FLEXML_REPLY VER="1.0"><REPLY_GET_ZONE_LOG RESULT="12" '
            'CMD_RESULT="ERROR"/></FLEXML_REPLY>',
            "zone",
            UTC,
        )


def _hass_with_entry(coordinator) -> MagicMock:
    entry = MagicMock()
    entry.entry_id = "abc"
    entry.state = ConfigEntryState.LOADED
    entry.runtime_data = coordinator
    hass = MagicMock()
    hass.config_entries.async_entries.return_value = [entry]
    return hass


def _call(**data) -> MagicMock:
    call = MagicMock()
    call.data = GET_LOG_SCHEMA(data)
    return call


@pytest.mark.asyncio
async def test_get_log_service_limits_and_passes_id() -> None:
    coordinator = MagicMock()
    coordinator.async_read_log = AsyncMock(
        return_value=parse_log(ACCESS_LOG, "access", UTC)
    )
    result = await _async_get_log(
        _hass_with_entry(coordinator), _call(log="access", id=3, limit=2)
    )
    coordinator.async_read_log.assert_awaited_once_with("access", 3)
    assert result["count"] == 2
    assert result["total"] == 3


@pytest.mark.asyncio
async def test_get_log_service_ignores_id_for_system_log() -> None:
    coordinator = MagicMock()
    coordinator.async_read_log = AsyncMock(return_value=[])
    await _async_get_log(_hass_with_entry(coordinator), _call(log="system", id=5))
    coordinator.async_read_log.assert_awaited_once_with("system", None)


@pytest.mark.asyncio
async def test_get_log_service_errors() -> None:
    coordinator = MagicMock()
    coordinator.async_read_log = AsyncMock(side_effect=FlexCCommandTimeout("slow"))
    hass = _hass_with_entry(coordinator)
    with pytest.raises(ServiceValidationError):
        await _async_get_log(hass, _call(log="access"))
    with pytest.raises(HomeAssistantError):
        await _async_get_log(hass, _call(log="zone", id=1))
    hass.config_entries.async_entries.return_value = []
    with pytest.raises(ServiceValidationError):
        await _async_get_log(hass, _call(log="system"))


@pytest.mark.parametrize(("event_id", "expected"), [("7013", True), ("7014", False)])
def test_mapping_gate_events_update_state(event_id, expected) -> None:
    coordinator = MagicMock(spec=SpcFlexCMappingGateCoordinator)
    coordinator.state = SpcState(
        mapping_gates={2: MappingGateState(mg_id=2, state=not expected)}
    )
    coordinator._apply_door_event.return_value = False
    event = {"EV_ID": event_id, "MG_ID": "2"}
    assert SpcFlexCMappingGateCoordinator._apply_event_state(coordinator, event)
    assert coordinator.state.mapping_gates[2].state is expected
    # Same state again, or an unknown gate: nothing changes.
    assert not SpcFlexCMappingGateCoordinator._apply_event_state(coordinator, event)
    assert not SpcFlexCMappingGateCoordinator._apply_event_state(
        coordinator, {"EV_ID": event_id, "MG_ID": "9"}
    )


def test_active_alerts_sensor() -> None:
    from custom_components.spc_flexc.sensor import SpcActiveAlertsSensor

    coordinator = MagicMock()
    coordinator.entry.entry_id = "test"
    coordinator.entry.data = {"host": "192.0.2.1"}
    coordinator.data = SpcState()
    sensor = SpcActiveAlertsSensor(coordinator)
    assert sensor.native_value == 0
    assert sensor.extra_state_attributes == {"alerts": []}
    coordinator.data.alerts = [{"event_id": 3006, "state": 1}]
    assert sensor.native_value == 1
    assert sensor.extra_state_attributes["alerts"] == [
        {"event_id": 3006, "state": 1, "description": "Door forced"}
    ]


def test_access_log_types_mapped_2026_11_13() -> None:
    """Types 6, 24 and 25 as the web page's access log shows them."""
    from custom_components.spc_flexc.flexc.logs import ACCESS_LOG_TYPES

    assert ACCESS_LOG_TYPES[6] == "door_left_open"
    assert ACCESS_LOG_TYPES[24] == "unknown_card"
    assert ACCESS_LOG_TYPES[25] == "code_lockout"


def test_result_codes_are_described() -> None:
    from custom_components.spc_flexc.flexc.flexml import describe_result

    assert (
        describe_result("78")
        == "RESULT='78' (not allowed while the panel is in installer mode)"
    )
    assert describe_result("65").endswith(
        "(not allowed for this login or command profile)"
    )
    assert describe_result("999") == "RESULT='999'"
