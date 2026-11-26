"""Door lock entity."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.spc_flexc.lock import SpcDoorLock
from custom_components.spc_flexc.models import DoorState, SpcState


def _lock(door: DoorState) -> tuple[SpcDoorLock, MagicMock]:
    coordinator = MagicMock()
    coordinator.entry.entry_id = "test"
    coordinator.data = SpcState(doors={door.door_id: door})
    coordinator.async_control_door = AsyncMock()
    return SpcDoorLock(coordinator, door.door_id), coordinator


def test_lock_state_from_mode_entry_granted_and_contact() -> None:
    door = DoorState(door_id=3)
    lock, _ = _lock(door)
    assert lock.unique_id == "test_door_3_lock"
    assert lock.is_locked is None
    door.mode = 0
    assert lock.is_locked is True
    door.mode = 1
    assert lock.is_locked is True
    door.mode = 2
    assert lock.is_locked is False
    door.mode = 0
    door.entry_granted_until = datetime.now(UTC) + timedelta(seconds=3)
    assert lock.is_locked is False
    door.entry_granted_until = datetime.now(UTC) - timedelta(seconds=1)
    assert lock.is_locked is True
    assert lock.is_open is None
    door.dps_input = 1
    assert lock.is_open is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "action"),
    [("async_lock", 7), ("async_unlock", 6), ("async_open", 5)],
)
async def test_lock_actions(method, action) -> None:
    lock, coordinator = _lock(DoorState(door_id=3, mode=0))
    await getattr(lock, method)()
    coordinator.async_control_door.assert_awaited_once_with(3, action, None)
