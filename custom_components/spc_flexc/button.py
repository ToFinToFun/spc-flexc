"""Button entities for SPC FlexC access-control door actions."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .entity_action import async_context_user_name, async_entity_action
from .entity_ids import with_spc_entity_ids
from .flexc.device import (
    build_door_device_info,
    build_panel_device_info,
    build_zone_device_info,
    door_placeholders,
    zone_placeholders,
)
from .zone_control_coordinator import SpcFlexCZoneControlCoordinator

# DOOR_STATUS flag that says whether the panel allows each door action.
DOOR_ACTION_PERMISSION = {
    "open_momentarily": "momentary_allowed",
    "open_permanently": "unlock_allowed",
    "set_normal": "normal_allowed",
    "lock": "lock_allowed",
}


# Door MODE (0 normal, 1 blocked, 2 unlocked) in which the web page does not
# offer an action. Checked on an SPC4300: normal shows Block/Unlock/Momentary,
# unlocked shows Normal/Block. Blocked is assumed to show Normal/Unlock/Momentary.
DOOR_ACTION_HIDDEN_IN_MODE: dict[str, tuple[int, ...]] = {
    "set_normal": (0,),
    "lock": (1,),
    "open_permanently": (2,),
    "open_momentarily": (2,),
}


@dataclass(frozen=True, kw_only=True)
class SpcDoorButtonDescription(ButtonEntityDescription):
    """Describe one SPC FlexC door action button."""

    action: int


DOOR_BUTTONS = (
    SpcDoorButtonDescription(
        key="open_momentarily", translation_key="open_momentarily", action=5
    ),
    SpcDoorButtonDescription(
        key="open_permanently", translation_key="open_permanently", action=6
    ),
    SpcDoorButtonDescription(key="set_normal", translation_key="set_normal", action=7),
    SpcDoorButtonDescription(key="lock", translation_key="lock", action=8),
)


class SpcZoneRestoreButton(
    CoordinatorEntity[SpcFlexCZoneControlCoordinator], ButtonEntity
):
    """Restore one SPC zone when the panel explicitly permits it."""

    _attr_has_entity_name = True
    _attr_translation_key = "restore"

    def __init__(
        self, coordinator: SpcFlexCZoneControlCoordinator, zone_id: int
    ) -> None:
        """Initialize a zone restore button."""
        super().__init__(coordinator)
        self.zone_id = zone_id
        zone = coordinator.data.zones[zone_id]
        self._attr_translation_placeholders = zone_placeholders(zone_id, zone)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_zone_{zone_id}_restore"
        self._attr_device_info = build_zone_device_info(coordinator, zone_id)

    @property
    def available(self) -> bool:
        """Return whether SPC currently permits restoring this zone."""
        zone = self.coordinator.data.zones.get(self.zone_id)
        return zone is not None and zone.restore_allowed is True

    @property
    def extra_state_attributes(self) -> dict[str, bool | int | None]:
        """Expose the zone identity and current restore permission."""
        zone = self.coordinator.data.zones.get(self.zone_id)
        return {
            "zone_id": self.zone_id,
            "restore_allowed": None if zone is None else zone.restore_allowed,
        }

    async def async_press(self) -> None:
        """Restore the zone using validated FlexC action 4."""
        await async_entity_action(self.coordinator.async_restore_zone(self.zone_id))


class SpcDoorActionButton(
    CoordinatorEntity[SpcFlexCZoneControlCoordinator], ButtonEntity
):
    """Represent one momentary SPC door-control action."""

    _attr_has_entity_name = True
    entity_description: SpcDoorButtonDescription

    def __init__(
        self,
        coordinator: SpcFlexCZoneControlCoordinator,
        door_id: int,
        description: SpcDoorButtonDescription,
    ) -> None:
        """Initialize a door action button."""
        super().__init__(coordinator)
        self.door_id = door_id
        self.entity_description = description
        self._attr_translation_placeholders = door_placeholders(coordinator, door_id)
        self._attr_unique_id = (
            f"{coordinator.entry.entry_id}_door_{door_id}_{description.key}"
        )
        self._attr_device_info = build_door_device_info(coordinator, door_id)

    @property
    def available(self) -> bool:
        """Known door, allowed by the panel and useful in the door's mode.

        Like the web page's Doors page: the *_ALLOWED flags stay 1 in every
        mode, so the page offers the actions by MODE (normal: Block, Unlock,
        Momentary; unlocked: Normal, Block).
        """
        door = self.coordinator.data.doors.get(self.door_id)
        if door is None:
            return False
        permission = DOOR_ACTION_PERMISSION.get(self.entity_description.key)
        if permission is not None and getattr(door, permission) is False:
            return False
        hidden_in = DOOR_ACTION_HIDDEN_IN_MODE.get(self.entity_description.key, ())
        return door.mode not in hidden_in

    async def async_press(self) -> None:
        """Send the Vanderbilt SPCLink-proven door action."""
        await async_entity_action(
            self.coordinator.async_control_door(
                self.door_id,
                self.entity_description.action,
                await async_context_user_name(self),
            )
        )


class SpcSilenceBellsButton(
    CoordinatorEntity[SpcFlexCZoneControlCoordinator], ButtonEntity
):
    """Silence all bells (CMD_SILENCE_ALL_BELLS); answers 0 (2026-11-13)."""

    _attr_has_entity_name = True
    _attr_translation_key = "silence_bells"
    _attr_icon = "mdi:bell-off"

    def __init__(self, coordinator: SpcFlexCZoneControlCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_silence_bells"
        self._attr_device_info = build_panel_device_info(coordinator)

    async def async_press(self) -> None:
        await async_entity_action(self.coordinator.async_silence_bells())


class SpcFlexCTestCallButton(
    CoordinatorEntity[SpcFlexCZoneControlCoordinator], ButtonEntity
):
    """Request a FlexC test call on one ATP; answers 0 (2026-11-13)."""

    _attr_has_entity_name = True
    _attr_translation_key = "flexc_test_call"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: SpcFlexCZoneControlCoordinator, ats_id: int, atp_id: int
    ) -> None:
        super().__init__(coordinator)
        self.ats_id = ats_id
        self.atp_id = atp_id
        atp = coordinator.data.ats[ats_id].atps[atp_id]
        self._attr_translation_placeholders = {"atp_name": atp.name or f"ATP {atp_id}"}
        self._attr_unique_id = (
            f"{coordinator.entry.entry_id}_ats_{ats_id}_atp_{atp_id}_test_call"
        )
        self._attr_device_info = build_panel_device_info(coordinator)

    async def async_press(self) -> None:
        atp = self.coordinator.data.ats[self.ats_id].atps[self.atp_id]
        await async_entity_action(
            self.coordinator.async_request_flexc_test(self.ats_id, atp.seq_id or 1)
        )


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up action buttons for dynamically discovered SPC doors."""
    async_add_entities = with_spc_entity_ids(
        "button", entry.entry_id, async_add_entities
    )
    coordinator: SpcFlexCZoneControlCoordinator = entry.runtime_data
    known_doors: set[int] = set()
    known_zones: set[int] = set()
    known_atps: set[tuple[int, int]] = set()
    panel_buttons_added = False

    def add_buttons() -> None:
        """Create panel, restore, door-action and ATP buttons."""
        nonlocal panel_buttons_added
        entities: list[ButtonEntity] = []
        if not panel_buttons_added:
            panel_buttons_added = True
            entities.append(SpcSilenceBellsButton(coordinator))
        for zone_id in coordinator.data.zones:
            if zone_id in known_zones:
                continue
            known_zones.add(zone_id)
            entities.append(SpcZoneRestoreButton(coordinator, zone_id))

        for door_id in coordinator.data.doors:
            if door_id in known_doors:
                continue
            known_doors.add(door_id)
            entities.extend(
                SpcDoorActionButton(coordinator, door_id, description)
                for description in DOOR_BUTTONS
            )
        for ats_id, ats in coordinator.data.ats.items():
            for atp_id in ats.atps:
                if (ats_id, atp_id) in known_atps:
                    continue
                known_atps.add((ats_id, atp_id))
                entities.append(SpcFlexCTestCallButton(coordinator, ats_id, atp_id))
        if entities:
            async_add_entities(entities)

    add_buttons()
    entry.async_on_unload(coordinator.async_add_listener(add_buttons))
