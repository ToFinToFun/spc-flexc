"""Zone status, the inhibited/isolated overview and number-first names."""

from unittest.mock import MagicMock

from custom_components.spc_flexc.flexc.device import numbered
from custom_components.spc_flexc.models import SpcState, XBusDeviceState, ZoneState
from custom_components.spc_flexc.sensor import (
    SpcInhibitedIsolatedSensor,
    zone_status,
)


def _zone(**values) -> ZoneState:
    raw = values.pop("raw", {"INHIBIT_ALLOWED": "1", "ISOLATE_ALLOWED": "1"})
    return ZoneState(zone_id=values.pop("zone_id", 9), raw=raw, **values)


def test_numbered_names_like_the_web_page() -> None:
    assert numbered(9, "Hall") == "9 Hall"
    assert numbered(9, None) == "Zone 9"
    assert numbered(2, "", "Output") == "Output 2"


def test_zone_status_order() -> None:
    assert zone_status(_zone(logic_input=0, status=0)) == "normal"
    assert zone_status(_zone(logic_input=1, status=0)) == "active"
    assert zone_status(_zone(logic_input=0, alarm_state=1)) == "alarm"
    assert zone_status(_zone(logic_input=3, input_state=3)) == "disconnected"
    assert zone_status(_zone(logic_input=3, input_state=6)) == "missing"
    assert zone_status(_zone(logic_input=0, event_tamper=True)) == "tamper"
    assert zone_status(_zone(logic_input=0, event_trouble=True)) == "trouble"
    # Isolated wins over everything, as on the web page.
    assert zone_status(_zone(logic_input=3, status=2, raw={})) == "isolated"
    assert zone_status(_zone(logic_input=0, status=1, raw={})) == "inhibited"
    assert zone_status(_zone(logic_input=None, raw={})) is None


def test_inhibited_isolated_lists_zones_and_xbus_bits() -> None:
    coordinator = MagicMock()
    coordinator.entry.entry_id = "test"
    coordinator.data = SpcState()
    coordinator.data.panel.serial_number = "SERIAL"
    coordinator.data.zones[31] = _zone(zone_id=31, name="Kitchen", status=2, raw={})
    coordinator.data.zones[9] = _zone(logic_input=0, status=0)
    coordinator.data.xbus_devices["AB"] = XBusDeviceState(
        device_id=2, name="IO 2", inhibit_raw="0000", isolate_raw="000A"
    )
    sensor = SpcInhibitedIsolatedSensor(coordinator)
    assert sensor.native_value == 3
    items = sensor.extra_state_attributes["items"]
    assert items[0] == {
        "kind": "zone",
        "id": 31,
        "name": "31 Kitchen",
        "state": "isolated",
    }
    assert [i["fault"] for i in items[1:]] == ["tamper", "mains_fault"]


def test_xbus_psu_sensors_read_the_raw_fields() -> None:
    from custom_components.spc_flexc.sensor import SpcXBusPsuSensor

    coordinator = MagicMock()
    coordinator.entry.entry_id = "test"
    coordinator.data = SpcState()
    coordinator.data.panel.serial_number = "SERIAL"
    coordinator.data.xbus_devices["IO"] = XBusDeviceState(
        device_id=2,
        name="IO 2",
        serial_number="IO",
        device_type=2,
        raw={"PSU_TYPE": "1", "PSU_BATT_VOLT": "13.7V", "PSU_OUT3_CURR": "225mA"},
    )
    volt = SpcXBusPsuSensor(coordinator, "IO", "PSU_BATT_VOLT")
    curr = SpcXBusPsuSensor(coordinator, "IO", "PSU_OUT3_CURR")
    assert volt.native_value == 13.7
    assert curr.native_value == 225.0
    assert volt.extra_state_attributes["psu_type"] == "1"
    assert curr.extra_state_attributes is None


def test_xbus_serial_shown_like_the_web_page() -> None:
    from custom_components.spc_flexc.flexc.device import xbus_serial_as_shown

    assert xbus_serial_as_shown("1EE227CA") == "518137802"
    assert xbus_serial_as_shown("X-1") == "X-1"
    assert xbus_serial_as_shown(None) is None


def test_xbus_status_like_the_web_page() -> None:
    from custom_components.spc_flexc.sensor import xbus_status

    def device(**raw):
        return XBusDeviceState(
            device_id=1,
            input_raw=raw.get("i", "0000"),
            alert_raw=raw.get("a", "0000"),
            inhibit_raw=raw.get("h", "0000"),
            isolate_raw=raw.get("s", "0000"),
        )

    assert xbus_status(device()) == "ok"
    assert xbus_status(device(i="0002", s="000A")) == "isolated"
    assert xbus_status(device(h="0002")) == "inhibited"
    assert xbus_status(device(i="0002")) == "fault"


def test_installed_languages_from_the_mask() -> None:
    from custom_components.spc_flexc.flexc.users import parse_installed_languages

    reply = (
        '<FLEXML_REPLY VER="1.0"><REPLY_READ_LANG_CFG RESULT="0" CMD_RESULT="OK">'
        '<LANGUAGE_STATUS LANGUAGES="00000081" /></REPLY_READ_LANG_CFG></FLEXML_REPLY>'
    )
    assert parse_installed_languages(reply) == [0, 7]


def test_door_buttons_follow_the_mode_like_the_web_page() -> None:
    from custom_components.spc_flexc.button import DOOR_BUTTONS, SpcDoorActionButton
    from custom_components.spc_flexc.models import DoorState

    coordinator = MagicMock()
    coordinator.entry.entry_id = "test"
    coordinator.data = SpcState()
    coordinator.data.panel.serial_number = "SERIAL"
    door = DoorState(door_id=1, mode=0)
    coordinator.data.doors[1] = door
    buttons = {d.key: SpcDoorActionButton(coordinator, 1, d) for d in DOOR_BUTTONS}

    def shown() -> set[str]:
        return {key for key, button in buttons.items() if button.available}

    assert shown() == {"lock", "open_permanently", "open_momentarily"}
    door.mode = 2
    assert shown() == {"set_normal", "lock"}
    door.mode = 1
    assert shown() == {"set_normal", "open_permanently", "open_momentarily"}
