"""Door configuration, event-driven door state, bus events and door entities."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from custom_components.spc_flexc.binary_sensor import (
    SpcDoorEntryGrantedSensor,
    SpcDoorOpenSensor,
)
from custom_components.spc_flexc.bus_events import (
    EVENT_SPC_FLEXC,
    async_fire_panel_event,
    build_event_data,
)
from custom_components.spc_flexc.button import DOOR_BUTTONS, SpcDoorActionButton
from custom_components.spc_flexc.coordinator import door_state_from_status
from custom_components.spc_flexc.flexc.flexml import (
    FlexMLError,
    FlexMLReplyError,
    build_door_config_command,
    parse_door_config,
)
from custom_components.spc_flexc.logbook import describe_panel_event
from custom_components.spc_flexc.models import DoorState, SpcState
from custom_components.spc_flexc.zone_control_coordinator import (
    ENTRY_GRANTED_FALLBACK_SECONDS,
    SpcFlexCZoneControlCoordinator,
)

# Shape of a real SPC4300 (firmware 3.16) reply; names are placeholders.
DOOR_CONFIG_REPLY = (
    '<FLEXML_REPLY VER="1.0"><REPLY_GET_DOOR_CONFIG RESULT="0" CMD_RESULT="OK">'
    '<DOOR_CONFIG DOOR_ID="3" ATTRIB="0520A212" GRANTED_TIME="3" DENY_TIME="1" '
    'OPEN_TIME="180" LEFT_TIME="60" EXT_TIME="10" ESCORT_TIME="10" '
    'DOOR_SIDE_1="1"  FIRE_AREA="0000000000000009"/>'
    '<DOOR_TRIGGER_CONFIG DOOR_ID="3" ACTION="3" TRIGGER="1" EDGE="0" />'
    "</REPLY_GET_DOOR_CONFIG></FLEXML_REPLY>"
)

# Field set sent by a real SPC4300 (firmware 3.16); names are placeholders.
SPC4300_DOOR_STATUS = {
    "DOOR_ID": "3",
    "DPS_INPUT": "0",
    "DRS_INPUT": "0",
    "STATUS": "0",
    "MODE": "0",
    "READER1_FORMAT": "255",
    "READER2_FORMAT": "255",
    "ZONE_ID": "25",
    "ZONE_NAME": "Front door",
    "AREA_ID": "1",
    "AREA_NAME": "House",
    "AREA_SIDE_2": "2",
    "AREA_SIDE_2_NAME": "Garage",
    "ENTRY_EXIT": "1",
    "LOCK_ALLOWED": "1",
    "UNLOCK_ALLOWED": "1",
    "MOMENTARY_ALLOWED": "0",
}


def test_build_door_config_command() -> None:
    command = build_door_config_command(3, "user", "pass")
    assert '<CMD_GET_DOOR_CONFIG DOOR_ID="3" />' in command


def test_parse_door_config_returns_door_fields() -> None:
    config = parse_door_config(DOOR_CONFIG_REPLY, 3)
    assert config["GRANTED_TIME"] == "3"
    assert config["OPEN_TIME"] == "180"


def test_parse_door_config_rejects_other_door_and_errors() -> None:
    with pytest.raises(FlexMLError):
        parse_door_config(DOOR_CONFIG_REPLY, 4)
    with pytest.raises(FlexMLReplyError):
        parse_door_config(
            '<FLEXML_REPLY VER="1.0"><REPLY_GET_DOOR_CONFIG RESULT="13" '
            'CMD_RESULT="ERROR"/></FLEXML_REPLY>',
            3,
        )


def test_door_state_reads_spc4300_fields_and_keeps_event_state() -> None:
    granted_at = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)
    previous = DoorState(
        door_id=3,
        granted_time=3,
        entry_granted_at=granted_at,
        entry_granted_until=granted_at + timedelta(seconds=3),
    )
    door = door_state_from_status(SPC4300_DOOR_STATUS, previous)
    assert door.name == "Front door"
    assert door.area_side_2 == 2
    assert door.area_side_2_name == "Garage"
    assert door.unlock_allowed is True
    assert door.momentary_allowed is False
    assert door.normal_allowed is None
    assert door.granted_time == 3
    assert door.entry_granted_at == granted_at


def _coordinator(door: DoorState) -> MagicMock:
    coordinator = MagicMock(spec=SpcFlexCZoneControlCoordinator)
    coordinator.hass = MagicMock()
    coordinator.state = SpcState(doors={door.door_id: door})
    coordinator._entry_granted_cancel = {}
    coordinator._start_entry_granted.side_effect = lambda d: (
        SpcFlexCZoneControlCoordinator._start_entry_granted(coordinator, d)
    )
    return coordinator


@pytest.mark.parametrize(
    ("granted_time", "expected_seconds"),
    [(5, 5), (None, ENTRY_GRANTED_FALLBACK_SECONDS)],
)
def test_entry_granted_event_marks_door_for_granted_time(
    granted_time, expected_seconds
) -> None:
    door = DoorState(door_id=3, granted_time=granted_time)
    coordinator = _coordinator(door)
    with patch(
        "custom_components.spc_flexc.zone_control_coordinator.async_call_later"
    ) as call_later:
        changed = SpcFlexCZoneControlCoordinator._apply_door_event(
            coordinator, {"EV_ID": "3000", "DOOR_ID": "3"}
        )
    assert changed is True
    assert door.entry_granted_until - door.entry_granted_at == timedelta(
        seconds=expected_seconds
    )
    assert call_later.call_args.args[1] == expected_seconds
    assert 3 in coordinator._entry_granted_cancel


def test_repeated_entry_granted_restarts_timer() -> None:
    door = DoorState(door_id=3, granted_time=3)
    coordinator = _coordinator(door)
    first_cancel = MagicMock()
    with patch(
        "custom_components.spc_flexc.zone_control_coordinator.async_call_later",
        side_effect=[first_cancel, MagicMock()],
    ):
        for _ in range(2):
            SpcFlexCZoneControlCoordinator._apply_door_event(
                coordinator, {"EV_ID": "3000", "DOOR_ID": "3"}
            )
    first_cancel.assert_called_once_with()


@pytest.mark.parametrize(
    ("event_id", "field", "value"),
    [
        ("3010", "dps_input", 1),
        ("3011", "dps_input", 0),
        ("3007", "mode", 0),
        ("3008", "mode", 1),
        ("3009", "mode", 2),
    ],
)
def test_door_events_update_position_and_mode(event_id, field, value) -> None:
    door = DoorState(door_id=3, dps_input=None, mode=None)
    coordinator = _coordinator(door)
    assert SpcFlexCZoneControlCoordinator._apply_door_event(
        coordinator, {"EV_ID": event_id, "DOOR_ID": "3"}
    )
    assert getattr(door, field) == value
    # The same event again changes nothing.
    assert not SpcFlexCZoneControlCoordinator._apply_door_event(
        coordinator, {"EV_ID": event_id, "DOOR_ID": "3"}
    )


def test_door_event_for_unknown_door_is_ignored() -> None:
    coordinator = _coordinator(DoorState(door_id=3))
    assert not SpcFlexCZoneControlCoordinator._apply_door_event(
        coordinator, {"EV_ID": "3010", "DOOR_ID": "9"}
    )


def test_event_data_passes_known_fields_only() -> None:
    event = {
        "EV_ID": "3000",
        "EV_SEQ": "42",
        "EV_GRP": "30",
        "EV_DESC": "Entry granted",
        "SIA_CODE": "DG",
        "SIA_ADDRESS": "3",
        "TIMESTAMP": "12433406112026",
        "DOOR_ID": "3",
        "DOOR_NAME": "Front door",
        "AREA_ID": "1",
        "AREA_NAME": "House",
        "USER_ID": "7",
        "USER_NAME": "Guest",
        "CARD_NO": "123456",
        "UNKNOWN": "x",
    }
    data = build_event_data(
        "entry", event, "Entry granted", ZoneInfo("Europe/Stockholm")
    )
    assert data["event_id"] == 3000
    assert data["sequence"] == 42
    assert data["door_id"] == 3
    assert data["user_id"] == 7
    assert data["user_name"] == "Guest"
    assert data["sia_code"] == "DG"
    assert data["panel_time"] == "2026-11-06T12:43:34+01:00"
    assert "CARD_NO" not in data and "card_no" not in data
    assert "UNKNOWN" not in data
    assert all(not key.isupper() for key in data)


def test_fire_panel_event_adds_description() -> None:
    hass = MagicMock()
    async_fire_panel_event(hass, "entry", {"EV_ID": "3010", "DOOR_ID": "3"}, UTC)
    name, data = hass.bus.async_fire.call_args.args
    assert name == EVENT_SPC_FLEXC
    assert data["description"] == "Door Open"
    assert data["panel_time"] is None


def test_logbook_description() -> None:
    assert describe_panel_event(
        {"door_name": "Front door", "panel_text": "Entry granted", "user_name": "Guest"}
    ) == {"name": "Front door", "message": "Entry granted (Guest)"}
    assert describe_panel_event({"zone_name": "Hall", "description": "Zone open"}) == {
        "name": "Hall",
        "message": "Zone open",
    }
    assert describe_panel_event({"event_id": 9999}) == {
        "name": "SPC",
        "message": "event 9999",
    }


def _entity_coordinator(door: DoorState) -> MagicMock:
    coordinator = MagicMock()
    coordinator.entry.entry_id = "test"
    coordinator.data = SpcState(doors={door.door_id: door})
    return coordinator


def test_entry_granted_sensor() -> None:
    door = DoorState(door_id=3, granted_time=3)
    sensor = SpcDoorEntryGrantedSensor(_entity_coordinator(door), 3)
    assert sensor.unique_id == "test_door_3_door_entry_granted"
    assert sensor.is_on is False
    now = datetime.now(UTC)
    door.entry_granted_at = now
    door.entry_granted_until = now + timedelta(seconds=3)
    assert sensor.is_on is True
    assert sensor.extra_state_attributes["granted_time"] == 3
    door.entry_granted_until = now - timedelta(seconds=1)
    assert sensor.is_on is False


def test_door_open_sensor() -> None:
    door = DoorState(door_id=3)
    sensor = SpcDoorOpenSensor(_entity_coordinator(door), 3)
    assert sensor.is_on is None
    door.dps_input = 1
    assert sensor.is_on is True
    door.dps_input = 0
    assert sensor.is_on is False


def test_door_button_follows_panel_permission() -> None:
    door = DoorState(door_id=3)
    coordinator = _entity_coordinator(door)
    buttons = {d.key: SpcDoorActionButton(coordinator, 3, d) for d in DOOR_BUTTONS}
    # Flags not reported: every action stays available.
    assert all(button.available for button in buttons.values())
    door.momentary_allowed = False
    door.lock_allowed = True
    assert buttons["open_momentarily"].available is False
    assert buttons["lock"].available is True
    assert buttons["set_normal"].available is True
