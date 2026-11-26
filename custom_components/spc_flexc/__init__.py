"""Home Assistant setup for the SPC FlexC integration."""

import logging
import re
from collections.abc import Mapping
from typing import cast

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.typing import ConfigType

from .const import CONF_SIDEBAR_PANEL, DOMAIN, PLATFORMS
from .frontend import async_register_card, async_set_panel
from .mapping_gate_coordinator import SpcFlexCMappingGateCoordinator
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the integration's services."""
    async_setup_services(hass)
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up SPC FlexC."""
    try:
        await async_register_card(hass)
        await async_set_panel(hass, entry.options.get(CONF_SIDEBAR_PANEL, True))
    except Exception:
        _LOGGER.exception("Could not register SPC FlexC dashboard card")

    coordinator = SpcFlexCMappingGateCoordinator(hass, entry)
    await coordinator.async_restore_panel_tamper()
    await coordinator.async_restore_area_history()
    await coordinator.async_restore_door_history()
    await coordinator.async_restore_pin_keys()
    await coordinator.activity.async_load()

    # Fast first refresh:
    # connection + PANEL_SUMMARY only.
    try:
        await coordinator.async_config_entry_first_refresh()
    except BaseException:
        await coordinator.async_shutdown()
        raise

    serial = coordinator.data.panel.serial_number

    if serial and entry.unique_id != str(serial):
        hass.config_entries.async_update_entry(
            entry,
            unique_id=str(serial),
        )

    entry.runtime_data = coordinator
    coordinator.loaded_options = dict(entry.options)

    # Apply alias changes after saving integration options.
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    # Remove stale zone and area entities only after complete discovery.
    # Restrict cleanup to the exact unique IDs owned by this config entry;
    # other entities (including renamed/customized entities) are untouched.
    zone_entity_pattern = re.compile(
        rf"^{re.escape(entry.entry_id)}_zone_(\d+)_(?:motion|tamper|trouble|inhibition|isolation|restore)$"
    )
    area_entity_pattern = re.compile(rf"^{re.escape(entry.entry_id)}_area_(\d+)$")
    orphan_cleanup_done = False

    def cleanup_orphan_entities() -> None:
        nonlocal orphan_cleanup_done
        if orphan_cleanup_done or not coordinator._discovery_complete:
            return
        # An empty discovery is not sufficient evidence to delete all zones.
        discovered_zones = coordinator._detected_zone_ids
        if not discovered_zones:
            _LOGGER.warning("Skipping orphan zone cleanup: no zones discovered")
            return
        discovered_areas = coordinator._detected_area_ids
        if not discovered_areas:
            _LOGGER.warning("Skipping orphan area cleanup: no areas discovered")
        registry = er.async_get(hass)
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
            zone_match = zone_entity_pattern.fullmatch(entity.unique_id)
            area_match = area_entity_pattern.fullmatch(entity.unique_id)
            if zone_match:
                if int(zone_match.group(1)) in discovered_zones:
                    continue
                kind, object_id = "zone", zone_match.group(1)
            elif area_match and discovered_areas:
                if int(area_match.group(1)) in discovered_areas:
                    continue
                kind, object_id = "area", area_match.group(1)
            else:
                continue
            # Never remove a currently loaded entity. Its platform owns its
            # lifecycle, even if a discovery result appears inconsistent.
            current_state = hass.states.get(entity.entity_id)
            if current_state is not None and current_state.state != STATE_UNAVAILABLE:
                _LOGGER.warning(
                    "Skipping orphan cleanup for active SPC entity %s",
                    entity.entity_id,
                )
                continue
            _LOGGER.info(
                "Removing orphan SPC %s entity %s (%s %s no longer discovered)",
                kind,
                entity.entity_id,
                kind,
                object_id,
            )
            registry.async_remove(entity.entity_id)
        # Remove only vanished SPC area devices, never the panel or a live area.
        # The device may still be referenced by other integrations or children.
        if discovered_areas:
            device_registry = dr.async_get(hass)
            serial = coordinator.data.panel.serial_number or entry.entry_id
            for device in dr.async_entries_for_config_entry(
                device_registry, entry.entry_id
            ):
                area_ids = [
                    int(match.group(1))
                    for identifier_domain, identifier in device.identifiers
                    if identifier_domain == DOMAIN
                    if (
                        match := re.fullmatch(
                            rf"{re.escape(str(serial))}_area_(\d+)", identifier
                        )
                    )
                ]
                # Areas are no longer devices (they live on the panel): every
                # former area device without entities or children goes.
                if len(area_ids) != 1:
                    continue
                if any(
                    entity.device_id == device.id
                    for entity in er.async_entries_for_device(
                        registry, device.id, include_disabled_entities=True
                    )
                ):
                    continue
                if any(
                    child.via_device_id == device.id
                    for child in cast(
                        Mapping[str, DeviceEntry], device_registry.devices
                    ).values()
                ):
                    continue
                if device.config_entries != {entry.entry_id}:
                    continue
                _LOGGER.info(
                    "Removing empty SPC area device %s (area %s)",
                    device.id,
                    area_ids[0],
                )
                device_registry.async_remove_device(device.id)
        orphan_cleanup_done = True

    entry.async_on_unload(coordinator.async_add_listener(cleanup_orphan_entities))

    # Do not await this. Platforms are already loaded and their coordinator
    # listeners can create dynamic entities as discovery completes.
    coordinator.async_start_background_discovery()

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload SPC FlexC."""
    ok = await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )

    if ok:
        await entry.runtime_data.async_shutdown()
        others = [
            e
            for e in hass.config_entries.async_entries(DOMAIN)
            if e.entry_id != entry.entry_id
            and e.state is ConfigEntryState.LOADED
            and e.options.get(CONF_SIDEBAR_PANEL, True)
        ]
        if not others:
            await async_set_panel(hass, False)

    return ok


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload when the options change (aliases, doors, sidebar ...).

    Not when only the data changes: logging the engineer in or out
    remembers or forgets its login there and must not restart the
    integration (that would end an engineer login kept only in memory).
    """
    coordinator = getattr(entry, "runtime_data", None)
    if coordinator is not None and getattr(coordinator, "loaded_options", None) == dict(
        entry.options
    ):
        return
    await hass.config_entries.async_reload(entry.entry_id)
