"""Door locks for SPC access-control doors.

The lock maps the door's modes to Home Assistant lock actions:

* lock   -> CMD_DOOR_CONTROL 7 (Door Normal: locked, cards still work)
* unlock -> CMD_DOOR_CONTROL 6 (Door Unlocked: free access)
* open   -> CMD_DOOR_CONTROL 5 (open momentarily)

The door is reported unlocked in mode Unlocked and while the lock relay is
energised after Entry Granted, and open while the door contact is open.
Mode Blocked (cards, codes and the exit button refused) has its own button.
All four were checked on the panel at door 3 (2026-11-10).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from homeassistant.components.lock import LockEntity, LockEntityFeature
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .entity_action import async_context_user_name, async_entity_action
from .entity_ids import with_spc_entity_ids
from .flexc.device import build_door_device_info, door_placeholders
from .models import DoorState
from .zone_control_coordinator import SpcFlexCZoneControlCoordinator

MODE_NORMAL = 0
MODE_UNLOCKED = 2
ACTION_MOMENTARY = 5
ACTION_UNLOCK = 6
ACTION_NORMAL = 7
# The lock is "locked" in Normal and Blocked mode while no entry is granted,
# "unlocked" in Unlocked mode or during an entry, and "open" while the door
# contact is open: a door is only secure when it is locked and closed.
DOOR_MODE_NAMES = {0: "normal", 1: "blocked", 2: "unlocked"}


class SpcDoorLock(CoordinatorEntity[SpcFlexCZoneControlCoordinator], LockEntity):
    """One SPC door as a Home Assistant lock."""

    _attr_has_entity_name = True
    _attr_translation_key = "door_lock"
    # The door buttons (Normal, Unlock, Momentary, Block) are the web page's
    # actions; this standard lock repeats three of them for lock cards, voice
    # assistants and HomeKit, so it is off unless the owner switches it on.
    _attr_entity_registry_enabled_default = False
    _attr_supported_features = LockEntityFeature.OPEN

    def __init__(
        self, coordinator: SpcFlexCZoneControlCoordinator, door_id: int
    ) -> None:
        super().__init__(coordinator)
        self.door_id = door_id
        self._attr_translation_placeholders = door_placeholders(coordinator, door_id)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_door_{door_id}_lock"
        self._attr_device_info = build_door_device_info(coordinator, door_id)

    def _door(self) -> DoorState | None:
        return self.coordinator.data.doors.get(self.door_id)

    @property
    def available(self) -> bool:
        return self._door() is not None

    @property
    def is_locked(self) -> bool | None:
        door = self._door()
        if door is None or door.mode is None:
            return None
        if door.mode == MODE_UNLOCKED:
            return False
        until = door.entry_granted_until
        return not (until is not None and datetime.now(UTC) < until)

    @property
    def is_open(self) -> bool | None:
        door = self._door()
        if door is None:
            return None
        return door.door_is_open

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        door = self._door()
        if door is None:
            return {}
        if door.mode is None:
            return {"door_mode": None}
        return {"door_mode": DOOR_MODE_NAMES.get(door.mode, str(door.mode))}

    async def async_lock(self, **kwargs: Any) -> None:
        await async_entity_action(
            self.coordinator.async_control_door(
                self.door_id, ACTION_NORMAL, await async_context_user_name(self)
            )
        )

    async def async_unlock(self, **kwargs: Any) -> None:
        await async_entity_action(
            self.coordinator.async_control_door(
                self.door_id, ACTION_UNLOCK, await async_context_user_name(self)
            )
        )

    async def async_open(self, **kwargs: Any) -> None:
        await async_entity_action(
            self.coordinator.async_control_door(
                self.door_id, ACTION_MOMENTARY, await async_context_user_name(self)
            )
        )


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Add a lock for every discovered door."""
    async_add_entities = with_spc_entity_ids("lock", entry.entry_id, async_add_entities)
    coordinator: SpcFlexCZoneControlCoordinator = entry.runtime_data
    known: set[int] = set()

    def add_locks() -> None:
        new = [door_id for door_id in coordinator.data.doors if door_id not in known]
        known.update(new)
        if new:
            async_add_entities(SpcDoorLock(coordinator, door_id) for door_id in new)

    add_locks()
    entry.async_on_unload(coordinator.async_add_listener(add_locks))
