"""Switch entities for SPC FlexC controls."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .entity_action import async_entity_action
from .entity_ids import with_spc_entity_ids
from .flexc.device import (
    build_panel_device_info,
    build_zone_device_info,
    zone_placeholders,
)
from .mapping_gate_coordinator import SpcFlexCMappingGateCoordinator


class SpcZoneInhibitionSwitch(
    CoordinatorEntity[SpcFlexCMappingGateCoordinator], SwitchEntity
):
    """Represent the inhibition state of one SPC zone."""

    _attr_has_entity_name = True
    _attr_translation_key = "inhibition"

    def __init__(
        self, coordinator: SpcFlexCMappingGateCoordinator, zone_id: int
    ) -> None:
        super().__init__(coordinator)
        self.zone_id = zone_id
        zone = coordinator.data.zones[zone_id]
        self._attr_translation_placeholders = zone_placeholders(zone_id, zone)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_zone_{zone_id}_inhibition"
        self._attr_device_info = build_zone_device_info(coordinator, zone_id)

    @property
    def is_on(self) -> bool | None:
        zone = self.coordinator.data.zones.get(self.zone_id)
        return None if zone is None else zone.inhibited

    @property
    def available(self) -> bool:
        zone = self.coordinator.data.zones.get(self.zone_id)
        return zone is not None and zone.inhibited is not None

    @property
    def extra_state_attributes(self) -> dict[str, bool | int | None]:
        zone = self.coordinator.data.zones.get(self.zone_id)
        if zone is None:
            return {}
        return {
            "zone_id": zone.zone_id,
            "inhibit_allowed": zone.inhibit_allowed,
            "deinhibit_allowed": zone.deinhibit_allowed,
        }

    async def async_turn_on(self, **kwargs: object) -> None:
        await async_entity_action(self.coordinator.async_inhibit_zone(self.zone_id))

    async def async_turn_off(self, **kwargs: object) -> None:
        await async_entity_action(self.coordinator.async_deinhibit_zone(self.zone_id))


class SpcZoneIsolationSwitch(
    CoordinatorEntity[SpcFlexCMappingGateCoordinator], SwitchEntity
):
    """Represent the isolation state of one SPC zone."""

    _attr_has_entity_name = True
    _attr_translation_key = "isolation"

    def __init__(
        self, coordinator: SpcFlexCMappingGateCoordinator, zone_id: int
    ) -> None:
        super().__init__(coordinator)
        self.zone_id = zone_id
        zone = coordinator.data.zones[zone_id]
        self._attr_translation_placeholders = zone_placeholders(zone_id, zone)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_zone_{zone_id}_isolation"
        self._attr_device_info = build_zone_device_info(coordinator, zone_id)

    @property
    def is_on(self) -> bool | None:
        zone = self.coordinator.data.zones.get(self.zone_id)
        return None if zone is None else zone.isolated

    @property
    def available(self) -> bool:
        zone = self.coordinator.data.zones.get(self.zone_id)
        return zone is not None and zone.isolated is not None

    @property
    def extra_state_attributes(self) -> dict[str, bool | int | None]:
        zone = self.coordinator.data.zones.get(self.zone_id)
        if zone is None:
            return {}
        return {
            "zone_id": zone.zone_id,
            "isolate_allowed": zone.isolate_allowed,
            "deisolate_allowed": zone.deisolate_allowed,
        }

    async def async_turn_on(self, **kwargs: object) -> None:
        await async_entity_action(self.coordinator.async_isolate_zone(self.zone_id))

    async def async_turn_off(self, **kwargs: object) -> None:
        await async_entity_action(self.coordinator.async_deisolate_zone(self.zone_id))


class SpcMappingGateSwitch(
    CoordinatorEntity[SpcFlexCMappingGateCoordinator], SwitchEntity
):
    """Represent one configured SPC Mapping Gate output."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SpcFlexCMappingGateCoordinator, mg_id: int) -> None:
        super().__init__(coordinator)
        self.mg_id = mg_id
        mapping_gate = coordinator.data.mapping_gates[mg_id]
        self._attr_translation_key = "mapping_gate"
        self._attr_translation_placeholders = {
            "mg_id": str(mg_id),
            "mg_name": mapping_gate.name or "",
        }
        self._attr_unique_id = f"{coordinator.entry.entry_id}_mapping_gate_{mg_id}"
        self._attr_device_info = build_panel_device_info(coordinator)

    @property
    def is_on(self) -> bool | None:
        mapping_gate = self.coordinator.data.mapping_gates.get(self.mg_id)
        return None if mapping_gate is None else mapping_gate.state

    @property
    def available(self) -> bool:
        mapping_gate = self.coordinator.data.mapping_gates.get(self.mg_id)
        return mapping_gate is not None and mapping_gate.state is not None

    @property
    def extra_state_attributes(self) -> dict[str, int | str | None]:
        mapping_gate = self.coordinator.data.mapping_gates.get(self.mg_id)
        if mapping_gate is None:
            return {}
        return {
            "mg_id": mapping_gate.mg_id,
            "mg_name": mapping_gate.name,
        }

    async def async_turn_on(self, **kwargs: object) -> None:
        await async_entity_action(
            self.coordinator.async_set_mapping_gate(self.mg_id, True)
        )

    async def async_turn_off(self, **kwargs: object) -> None:
        await async_entity_action(
            self.coordinator.async_set_mapping_gate(self.mg_id, False)
        )


class SpcEngineerModeSwitch(
    CoordinatorEntity[SpcFlexCMappingGateCoordinator], SwitchEntity
):
    """Enter or exit full engineer mode with the engineer login.

    Available while an engineer is logged in (SPC app or setup). The state
    is the panel's ENG_MODE from the panel summary.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "engineer_mode_control"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:account-hard-hat"

    def __init__(self, coordinator: SpcFlexCMappingGateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_engineer_mode_control"
        self._attr_device_info = build_panel_device_info(coordinator)

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.has_engineer_login

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.panel.engineer_mode

    async def async_turn_on(self, **kwargs) -> None:
        await async_entity_action(self.coordinator.async_set_engineer_mode(True))

    async def async_turn_off(self, **kwargs) -> None:
        await async_entity_action(self.coordinator.async_set_engineer_mode(False))


class SpcSystemAlertControlSwitch(
    CoordinatorEntity[SpcFlexCMappingGateCoordinator], SwitchEntity
):
    """Inhibit or isolate one system alert (CMD_ALERT_CONTROL).

    Checked on the panel 2026-11-13 (ALERT_ID is the SYSALERT bit). The
    panel status is read back after every change and a mismatch is reported
    as an error. Enabled by default (owner 2026-11-13), like the web page's
    isolate buttons.
    """

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self, coordinator: SpcFlexCMappingGateCoordinator, key: str, kind: str
    ) -> None:
        super().__init__(coordinator)
        self.key = key
        self.kind = kind  # "inhibit" or "isolate"
        self._attr_translation_key = f"system_alert_{key}_{kind}"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_system_alert_{key}_{kind}"
        self._attr_device_info = build_panel_device_info(coordinator)

    def _state(self):
        return self.coordinator.data.system_alerts.get(self.key)

    @property
    def available(self) -> bool:
        return self._state() is not None

    @property
    def is_on(self) -> bool | None:
        state = self._state()
        if state is None:
            return None
        return state.inhibited if self.kind == "inhibit" else state.isolated

    async def _set(self, on: bool) -> None:
        action = {
            ("inhibit", True): 0,
            ("inhibit", False): 1,
            ("isolate", True): 2,
            ("isolate", False): 3,
        }[(self.kind, on)]
        await async_entity_action(
            self.coordinator.async_alert_control(self.key, action)
        )

    async def async_turn_on(self, **kwargs) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._set(False)


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up SPC FlexC switches."""
    async_add_entities = with_spc_entity_ids(
        "switch", entry.entry_id, async_add_entities
    )
    coordinator: SpcFlexCMappingGateCoordinator = entry.runtime_data
    # Always there; available while an engineer is logged in (SPC app).
    async_add_entities([SpcEngineerModeSwitch(coordinator)])
    known_inhibition_zones: set[int] = set()
    known_isolation_zones: set[int] = set()
    known_mapping_gates: set[int] = set()
    known_alert_controls: set[tuple[str, str]] = set()

    def add_switches() -> None:
        entities: list[SwitchEntity] = []
        for zone_id, zone in coordinator.data.zones.items():
            if zone_id not in known_inhibition_zones and (
                zone.inhibit_allowed is True or zone.inhibited is True
            ):
                known_inhibition_zones.add(zone_id)
                entities.append(SpcZoneInhibitionSwitch(coordinator, zone_id))
            if zone_id not in known_isolation_zones and (
                zone.isolate_allowed is True or zone.isolated is True
            ):
                known_isolation_zones.add(zone_id)
                entities.append(SpcZoneIsolationSwitch(coordinator, zone_id))

        for key, alert_state in coordinator.data.system_alerts.items():
            for kind, allowed in (
                ("inhibit", alert_state.inhibit_allowed),
                ("isolate", alert_state.isolate_allowed),
            ):
                if allowed and (key, kind) not in known_alert_controls:
                    known_alert_controls.add((key, kind))
                    entities.append(SpcSystemAlertControlSwitch(coordinator, key, kind))

        for mg_id in coordinator.data.mapping_gates:
            if mg_id in known_mapping_gates:
                continue
            known_mapping_gates.add(mg_id)
            entities.append(SpcMappingGateSwitch(coordinator, mg_id))

        if entities:
            async_add_entities(entities)

    add_switches()
    entry.async_on_unload(coordinator.async_add_listener(add_switches))
