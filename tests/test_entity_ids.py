"""Entity IDs come from the panel's numbers, not from names."""

from unittest.mock import MagicMock

from custom_components.spc_flexc.entity_ids import object_id, with_spc_entity_ids


def test_object_ids_follow_one_pattern() -> None:
    assert object_id("E", "E_zone_25_motion") == "spc_zone_25"
    assert object_id("E", "E_zone_25_inhibition") == "spc_zone_25_inhibition"
    assert object_id("E", "E_door_3_door_exit_button") == "spc_door_3_exit_button"
    assert object_id("E", "E_door_3_lock") == "spc_door_3_lock"
    assert object_id("E", "E_area_1") == "spc_area_1"
    assert object_id("E", "E_xbus_1618E3B3_status") == "spc_xbus_1618e3b3_status"
    assert object_id("E", "E_panel_alarm") == "spc_alarm"


def test_add_entities_sets_suggested_ids_only_when_missing() -> None:
    added: list[object] = []
    add = with_spc_entity_ids("switch", "E", added.extend)
    new = MagicMock(entity_id=None, unique_id="E_zone_9_isolation")
    preset = MagicMock(entity_id="switch.custom", unique_id="E_zone_9_inhibition")
    add([new, preset])
    assert new.entity_id == "switch.spc_zone_9_isolation"
    assert preset.entity_id == "switch.custom"
    assert added == [new, preset]


async def test_keep_clock_right_only_when_off_and_not_too_often() -> None:
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from custom_components.spc_flexc.coordinator import SpcFlexCCoordinator

    coordinator = SpcFlexCCoordinator.__new__(SpcFlexCCoordinator)
    coordinator.entry = SimpleNamespace(options={})
    coordinator.client = MagicMock(command_username="u", command_password="p")
    coordinator.client.async_send_flexml = AsyncMock(
        return_value='<FLEXML_REPLY VER="1.0"><REPLY_SET_CLOCK RESULT="0" CMD_RESULT="OK"/></FLEXML_REPLY>'
    )
    coordinator.state = SimpleNamespace(panel=SimpleNamespace(clock_offset=2))
    await coordinator._async_keep_clock_right_locked()
    assert coordinator.client.async_send_flexml.await_count == 0  # within 3 s
    coordinator.state.panel.clock_offset = -58
    await coordinator._async_keep_clock_right_locked()
    assert coordinator.client.async_send_flexml.await_count == 1
    assert coordinator.state.panel.clock_offset == 0
    coordinator.state.panel.clock_offset = -30
    await coordinator._async_keep_clock_right_locked()
    assert coordinator.client.async_send_flexml.await_count == 1  # once an hour
    coordinator._clock_synced_at = -1e9
    coordinator.entry.options = {"keep_clock_right": False}
    await coordinator._async_keep_clock_right_locked()
    assert coordinator.client.async_send_flexml.await_count == 1  # switched off
