"""Door lock entities from before 2.0.0-beta.8 are removed at setup."""

from unittest.mock import MagicMock, patch

from custom_components.spc_flexc import _remove_door_lock_entities


def test_only_lock_entities_of_this_entry_are_removed() -> None:
    entities = [
        MagicMock(domain="lock", entity_id="lock.spc_door_1_lock"),
        MagicMock(domain="button", entity_id="button.spc_door_1_lock"),
        MagicMock(domain="sensor", entity_id="sensor.spc_door_1_mode"),
    ]
    registry = MagicMock()
    entry = MagicMock(entry_id="abc")
    with (
        patch("custom_components.spc_flexc.er.async_get", return_value=registry),
        patch(
            "custom_components.spc_flexc.er.async_entries_for_config_entry",
            return_value=entities,
        ) as entries,
    ):
        _remove_door_lock_entities(MagicMock(), entry)

    entries.assert_called_once_with(registry, "abc")
    registry.async_remove.assert_called_once_with("lock.spc_door_1_lock")
