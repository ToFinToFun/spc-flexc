"""Sensor entities for the SPC FlexC integration."""

from datetime import datetime, timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfFrequency,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .capabilities import WORKS, capability_report
from .const import CONF_WIRELESS_RADIO_IDS, DOMAIN, SPC_ZONE_TYPES, XBUS_MASK_BITS
from .coordinator import SpcFlexCCoordinator
from .entity_ids import with_spc_entity_ids
from .flexc.device import (
    build_door_device_info,
    build_wireless_device_info,
    build_xbus_device_info,
    build_zone_device_info,
    door_placeholders,
    migrate_xbus_registry_identity,
    numbered,
    zone_placeholders,
)
from .flexc.intruder_config import decode_system_settings
from .flexc.users import spc_date
from .models import AtpState, DoorState


def _iso(value: object) -> str | None:
    return value.isoformat() if value is not None else None  # type: ignore[attr-defined]


DESCRIPTIONS = (
    SensorEntityDescription(
        key="battery_voltage",
        translation_key="battery_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
    ),
    SensorEntityDescription(
        key="aux_voltage",
        translation_key="aux_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
    ),
    SensorEntityDescription(
        key="aux_current",
        translation_key="aux_current",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
    ),
    SensorEntityDescription(
        key="ac_frequency",
        translation_key="ac_frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
    ),
    SensorEntityDescription(
        key="clock_offset",
        translation_key="clock_offset",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:clock-alert-outline",
    ),
    SensorEntityDescription(
        key="configuration_changed",
        translation_key="configuration_changed",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="users_changed",
        translation_key="users_changed",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities = with_spc_entity_ids(
        "sensor", entry.entry_id, async_add_entities
    )
    coordinator: SpcFlexCCoordinator = entry.runtime_data
    async_add_entities(
        [SpcPanelSensor(coordinator, description) for description in DESCRIPTIONS]
        + [
            SpcLastEventDiagnosticSensor(coordinator),
            SpcActiveAlertsSensor(coordinator),
            SpcPanelSettingsSensor(coordinator),
            SpcUsersSensor(coordinator),
            SpcUserProfilesSensor(coordinator),
            SpcCapabilitiesSensor(coordinator),
            SpcPirSlowReadDiagnosticSensor(coordinator),
            SpcInhibitedIsolatedSensor(coordinator),
            SpcUnknownCardsSensor(coordinator),
        ]
    )
    known_ats: set[int] = set()
    known_atps: set[tuple[int, int]] = set()
    known_doors: set[int] = set()
    known_xbus: set[str] = set()
    known_radios: set[str] = set()
    known_zones: set[int] = set()

    def add_dynamic_entities() -> None:
        entities: list[SensorEntity] = []
        for ats_id, ats in coordinator.data.ats.items():
            if ats_id not in known_ats:
                known_ats.add(ats_id)
                entities.append(SpcAtsActivePathSensor(coordinator, ats_id))
            for atp_id in ats.atps:
                key = (ats_id, atp_id)
                if key in known_atps:
                    continue
                known_atps.add(key)
                entities.append(SpcAtpLastTxSensor(coordinator, ats_id, atp_id))

        configured = coordinator.entry.options.get(CONF_WIRELESS_RADIO_IDS) or {}
        waiting = {
            str(radio_id)
            for zone_id, radio_id in configured.items()
            if not str(zone_id).isdigit() or int(zone_id) not in coordinator.data.zones
        }
        for radio_id in [*configured.values(), *coordinator.data.wireless_sensors]:
            if radio_id in waiting:
                continue  # named after its zone, so wait until the zone is read
            if radio_id in known_radios:
                continue
            known_radios.add(radio_id)
            entities.append(SpcWirelessSensor(coordinator, radio_id))

        for zone_id in coordinator.data.zones:
            if zone_id not in known_zones:
                known_zones.add(zone_id)
                entities.append(SpcZoneStatusSensor(coordinator, zone_id))

        for door_id in coordinator.data.doors:
            if door_id in known_doors:
                continue
            known_doors.add(door_id)
            entities.extend(
                (
                    SpcDoorStatusSensor(coordinator, door_id),
                    SpcDoorModeSensor(coordinator, door_id),
                )
            )

        for device_id, device in coordinator.data.xbus_devices.items():
            if device_id in known_xbus:
                continue
            known_xbus.add(device_id)
            for suffix in ("aux_voltage", "aux_current", "diagnostics", "device_id"):
                migrate_xbus_registry_identity(coordinator, device_id, "sensor", suffix)
            if device.device_type in (2, 6):
                for suffix in ("input_count", "output_count"):
                    migrate_xbus_registry_identity(
                        coordinator, device_id, "sensor", suffix
                    )
            entities.extend(
                (
                    SpcXBusAuxVoltageSensor(coordinator, device_id),
                    SpcXBusAuxCurrentSensor(coordinator, device_id),
                    SpcXBusDiagnosticSensor(coordinator, device_id),
                    SpcXBusStatusSensor(coordinator, device_id),
                    SpcXBusInventorySensor(
                        coordinator, device_id, "device_id", diagnostic=True
                    ),
                )
            )
            entities.extend(
                SpcXBusPsuSensor(coordinator, device_id, field)
                for field in XBUS_PSU_FIELDS
                if field in (device.raw or {})
            )
            if device.device_type in (2, 6):
                entities.extend(
                    (
                        SpcXBusInventorySensor(coordinator, device_id, "input_count"),
                        SpcXBusInventorySensor(coordinator, device_id, "output_count"),
                    )
                )

        if entities:
            async_add_entities(entities)

    add_dynamic_entities()
    entry.async_on_unload(coordinator.async_add_listener(add_dynamic_entities))


# Validated FlexC IDs from SPC event tables and field diagnostics.
# Descriptions are diagnostic metadata, not persistent alarm states.
FLEXC_EVENT_DESCRIPTIONS: dict[int, str] = {
    3000: "Entry granted",
    3001: "Entry denied",
    3002: "Exit granted",
    3003: "Exit denied",
    3004: "Door open too long",
    3005: "Door left open",
    3006: "Door forced",
    3007: "Door normal",
    3008: "Door locked (access denied)",
    3009: "Door unlocked (free access)",
    3010: "Door opened",
    3011: "Door closed",
    3012: "Door release (DRS)",
    3013: "Door alarm restored",
    3014: "Unknown card",
    3015: "Reader locked",
    3016: "Reader unlocked",
    2100: "Zone input active",
    2101: "Zone input restored",
    2103: "Zone input disconnected",
    2107: "Zone input out of bounds",
    1200: "Zone tamper",
    1300: "Zone tamper restored",
    1800: "Zone trouble",
    1900: "Zone trouble restored",
    4002: "User panic",
    4009: "User medical alarm",
    4011: "User hold-up",
    3523: "Confirmed hold-up",
    8026: "Wireless keypad medical alarm",
    8027: "Wireless keypad medical restore",
    8028: "Wireless keypad fire alarm",
    8029: "Wireless keypad fire restore",
    8030: "Wireless keypad panic alarm",
    8031: "Wireless keypad panic restore",
    5348: "X-BUS keypad panic alarm",
    5349: "X-BUS keypad panic restore",
    5350: "X-BUS keypad fire alarm",
    5351: "X-BUS keypad fire restore",
    5352: "X-BUS keypad medical alarm",
    5353: "X-BUS keypad medical restore",
    8006: "Wireless device tamper",
    8007: "Wireless device tamper restore",
    8012: "Wireless device low battery",
    8013: "Wireless device battery restore",
    8014: "Wireless device fault",
    8015: "Wireless device fault restore",
    6002: "FlexC path down",
    6003: "FlexC path restored",
    6004: "ATS down",
    6005: "ATS restored",
    7011: "Configuration changed",
    3501: "Area unset",
    3502: "Area Part Set A",
    3503: "Area Part Set B",
    3504: "Area Full Set",
    4003: "User logged in at keypad",
    4004: "User logged out at keypad",
    6000: "Network fault",
    6001: "Network restored",
    6008: "EDP receiver down",
    6009: "EDP receiver restored",
    7002: "Date and time changed",
    7003: "Engineer mode on",
    7004: "Engineer mode off",
    7013: "Mapping Gate on",
    7014: "Mapping Gate off",
}


# Zone event suffixes identify the SPC zone type. Names below are
# documented mappings; other suffixes retain their numeric type rather
# than guessing a misleading human-readable label.
FLEXC_ZONE_EVENT_TYPES: dict[int, str] = {
    0: "Alarm Zone",
    1: "Entry / Exit",
    3: "Fire",
    8: "Tamper",
    12: "Unused Zone",
    15: "Detector Fault",
    23: "Glass Break",
}

for _base, _prefix, _restored in (
    (1200, "Zone tamper", False),
    (1300, "Zone tamper", True),
    (1800, "Zone trouble", False),
    (1900, "Zone trouble", True),
):
    for _suffix in range(24):
        _zone_type = FLEXC_ZONE_EVENT_TYPES.get(_suffix, f"Zone type {_suffix}")
        FLEXC_EVENT_DESCRIPTIONS[_base + _suffix] = (
            f"{_prefix} restored [{_zone_type}]"
            if _restored
            else f"{_prefix} [{_zone_type}]"
        )


# Origin is intentionally separate from alarm state: user-triggered panic
# events may not provide AREA_ID or a matching restore event.
def _flexc_event_origin(event_id: int) -> str | None:
    if event_id in (4002, 4009, 4011, 3523):
        return "user"
    if event_id in (8026, 8027, 8028, 8029, 8030, 8031):
        return "wireless_keypad"
    if event_id in (5348, 5349, 5350, 5351, 5352, 5353):
        return "xbus_keypad"
    if event_id in (8006, 8007, 8012, 8013, 8014, 8015):
        return "wireless_device"
    if event_id in (6002, 6003, 6004, 6005):
        return "communication"
    if event_id == 7011:
        return "configuration"
    return None


# Transient events are diagnostic observations, not latched alarm states.
FLEXC_ALARM_EVENTS: dict[int, tuple[str, str]] = {
    4002: ("panic", "trigger"),
    4009: ("medical", "trigger"),
    4011: ("hold_up", "trigger"),
    3523: ("hold_up", "confirmed"),
    8026: ("medical", "trigger"),
    8027: ("medical", "restore"),
    8028: ("fire", "trigger"),
    8029: ("fire", "restore"),
    8030: ("panic", "trigger"),
    8031: ("panic", "restore"),
    5348: ("panic", "trigger"),
    5349: ("panic", "restore"),
    5350: ("fire", "trigger"),
    5351: ("fire", "restore"),
    5352: ("medical", "trigger"),
    5353: ("medical", "restore"),
}


class SpcPirSlowReadDiagnosticSensor(
    CoordinatorEntity[SpcFlexCCoordinator], SensorEntity
):
    """Optional, rolling one-hour diagnostic history of slow PIR zone reads."""

    _attr_has_entity_name = True
    _attr_name = "PIR slow reads (1h)"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False
    _attr_icon = "mdi:timer-alert-outline"

    def __init__(self, coordinator: SpcFlexCCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id(coordinator)}_pir_slow_reads_1h"
        self._attr_device_info = build_device_info(coordinator)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # Expire rolling history even when no new slow readings arrive.
        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self._async_refresh_history,
                timedelta(minutes=1),
            )
        )

    async def _async_refresh_history(self, _now: datetime) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> int:
        return self.coordinator.pir_slow_reads.snapshot()["count"]

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        snapshot = self.coordinator.pir_slow_reads.snapshot()
        return {
            "max_read_ms": snapshot["max_read_ms"],
            "slow_reads": snapshot["slow_reads"],
        }


class SpcLastEventDiagnosticSensor(
    CoordinatorEntity[SpcFlexCCoordinator], SensorEntity
):
    """Expose bounded FlexC event identifiers without verbose INFO logging."""

    _attr_has_entity_name = True
    _attr_translation_key = "last_flexc_event_id"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: SpcFlexCCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id(coordinator)}_last_flexc_event_id"
        self._attr_device_info = build_device_info(coordinator)

    @property
    def native_value(self) -> int | None:
        last = getattr(self.coordinator, "_last_event_identifiers", None)
        return last["event_id"] if last is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        last = getattr(self.coordinator, "_last_event_identifiers", None)
        if last is None:
            return {"recent_events": []}
        alarm = FLEXC_ALARM_EVENTS.get(last["event_id"])
        return {
            "area_id": last["area_id"],
            "zone_id": last["zone_id"],
            "event_description": FLEXC_EVENT_DESCRIPTIONS.get(last["event_id"]),
            "event_origin": _flexc_event_origin(last["event_id"]),
            "alarm_type": alarm[0] if alarm else None,
            "alarm_transition": alarm[1] if alarm else None,
            "recent_events": [
                {
                    "area_name": (
                        self.coordinator.data.areas[event["area_id"]].name
                        if event["area_id"] in self.coordinator.data.areas
                        else None
                    ),
                    "zone_name": (
                        self.coordinator.data.zones[event["zone_id"]].name
                        if event["zone_id"] in self.coordinator.data.zones
                        else None
                    ),
                    **event,
                    "description": FLEXC_EVENT_DESCRIPTIONS.get(event["event_id"]),
                    "origin": _flexc_event_origin(event["event_id"]),
                    "alarm_type": FLEXC_ALARM_EVENTS.get(
                        event["event_id"], (None, None)
                    )[0],
                    "alarm_transition": FLEXC_ALARM_EVENTS.get(
                        event["event_id"], (None, None)
                    )[1],
                }
                for event in getattr(self.coordinator, "_recent_event_identifiers", [])
            ],
        }


class SpcActiveAlertsSensor(CoordinatorEntity[SpcFlexCCoordinator], SensorEntity):
    """Number of active system alerts reported by GET_ALERT_STATUS."""

    _attr_has_entity_name = True
    _attr_translation_key = "active_alerts"
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, coordinator: SpcFlexCCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id(coordinator)}_active_alerts"
        self._attr_device_info = build_device_info(coordinator)

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.alerts)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        return {
            "alerts": [
                {
                    **alert,
                    "description": FLEXC_EVENT_DESCRIPTIONS.get(alert["event_id"])
                    if alert["event_id"] is not None
                    else None,
                }
                for alert in self.coordinator.data.alerts
            ]
        }


class SpcUsersSensor(CoordinatorEntity[SpcFlexCCoordinator], SensorEntity):
    """Number of panel users, with the users (no codes or card numbers) as attributes."""

    _attr_has_entity_name = True
    _attr_translation_key = "users"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:account-group"

    def __init__(self, coordinator: SpcFlexCCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id(coordinator)}_users"
        self._attr_device_info = build_device_info(coordinator)

    @property
    def available(self) -> bool:
        return bool(self.coordinator.data.users)

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.users)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        return {
            "pin_managed_numbers": {
                str(number): status
                for number, status in self.coordinator.pin_managed_numbers().items()
            },
            "users": [
                {
                    "user_id": user.user_id,
                    "name": user.name,
                    "profiles": list(user.profiles),
                    "valid_from": _iso(spc_date(user.start_date)),
                    "valid_until": _iso(spc_date(user.end_date)),
                    "has_card": user.has_card,
                    "card_number": user.card_number,
                    "card_options": list(user.card_flags),
                    "language": user.language,
                    "user_attrib": user.user_attrib,
                    "pin_managed": self.coordinator.pin_management(user.user_id),
                }
                for user in sorted(
                    self.coordinator.data.users.values(), key=lambda u: u.user_id
                )
            ],
        }


class SpcUserProfilesSensor(CoordinatorEntity[SpcFlexCCoordinator], SensorEntity):
    """Number of user profiles, with the profiles as attributes."""

    _attr_has_entity_name = True
    _attr_translation_key = "user_profiles"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:account-key"

    def __init__(self, coordinator: SpcFlexCCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id(coordinator)}_user_profiles"
        self._attr_device_info = build_device_info(coordinator)

    @property
    def available(self) -> bool:
        return bool(self.coordinator.data.user_profiles)

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.user_profiles)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        return {
            "profiles": [
                {
                    "profile_id": profile.profile_id,
                    "name": profile.name,
                    "areas": list(profile.areas),
                    "calendar": profile.calendar,
                    "doors": {str(k): v for k, v in profile.doors.items()},
                    "user_rights": profile.user_rights,
                    "user_rights2": profile.user_rights2,
                }
                for profile in sorted(
                    self.coordinator.data.user_profiles.values(),
                    key=lambda p: p.profile_id,
                )
            ]
        }


class SpcWirelessSensor(CoordinatorEntity[SpcFlexCCoordinator], SensorEntity):
    """One wireless sensor heard by the panel; state = when it was last heard.

    The wireless log names a sensor by its radio ID only, not by its zone.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "wireless_sensor"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:access-point"

    def __init__(self, coordinator: SpcFlexCCoordinator, radio_id: str) -> None:
        super().__init__(coordinator)
        self.radio_id = radio_id
        if self._zone_id() is not None:
            # Named after its zone, like the other zone entities.
            self._attr_translation_key = "wireless_zone_sensor"
        self._set_name()
        self._attr_unique_id = f"{entry_id(coordinator)}_wireless_{radio_id}"
        self._attr_device_info = build_wireless_device_info(coordinator)

    def _entry(self) -> dict[str, object] | None:
        return self.coordinator.data.wireless_sensors.get(self.radio_id)

    def _set_name(self) -> None:
        """Name it after its zone (added only once the zone is read)."""
        zone_id = self._zone_id()
        zone = self.coordinator.data.zones.get(zone_id) if zone_id else None
        placeholders = {"radio_id": self.radio_id}
        if zone_id is not None:
            placeholders.update(zone_placeholders(zone_id, zone))
        self._attr_translation_placeholders = placeholders

    def _zone_id(self) -> int | None:
        """The zone the owner set for this radio ID in the options."""
        configured = self.coordinator.entry.options.get(CONF_WIRELESS_RADIO_IDS) or {}
        for zone_id, radio_id in configured.items():
            if str(radio_id) == self.radio_id and str(zone_id).isdigit():
                return int(zone_id)
        return None

    @property
    def available(self) -> bool:
        return self._entry() is not None or self._zone_id() is not None

    @property
    def native_value(self) -> datetime | None:
        entry = self._entry()
        value = entry.get("last_seen") if entry else None
        return datetime.fromisoformat(str(value)) if value else None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        entry = self._entry() or {}
        zone_id = self._zone_id()
        zone = self.coordinator.data.zones.get(zone_id) if zone_id else None
        area = (
            self.coordinator.data.areas.get(zone.area_id)
            if zone and zone.area_id is not None
            else None
        )
        return {
            "radio_id": self.radio_id,
            "zone_id": zone_id,
            "zone_name": zone.name if zone else None,
            "area_name": area.name if area else (zone.area_name if zone else None),
            "signal": entry.get("signal"),
            "battery": entry.get("battery"),
            "status": entry.get("status"),
            "receiver_id": entry.get("receiver_id"),
            "lines_in_latest_log": entry.get("heard"),
        }


class SpcCapabilitiesSensor(CoordinatorEntity[SpcFlexCCoordinator], SensorEntity):
    """What the integration can do on this panel; state = functions that work."""

    _attr_has_entity_name = True
    _attr_translation_key = "capabilities"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:format-list-checks"

    def __init__(self, coordinator: SpcFlexCCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id(coordinator)}_capabilities"
        self._attr_device_info = build_device_info(coordinator)

    def _report(self) -> list[dict[str, object]]:
        return capability_report(
            getattr(self.coordinator, "command_results", {}),
            bool(getattr(self.coordinator, "has_engineer_login", False)),
        )

    @property
    def native_value(self) -> int:
        return sum(1 for entry in self._report() if entry["status"] == WORKS)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        report = self._report()
        counts: dict[str, int] = {}
        for entry in report:
            counts[str(entry["status"])] = counts.get(str(entry["status"]), 0) + 1
        return {
            "command_login": self.coordinator.data.command_login or None,
            "engineer_login": getattr(
                self.coordinator, "engineer_session", {"logged_in": False}
            ),
            "engineer_mode": self.coordinator.data.panel.engineer_mode,
            "counts": counts,
            "functions": report,
        }


class SpcPanelSettingsSensor(CoordinatorEntity[SpcFlexCCoordinator], SensorEntity):
    """Panel system options and timers (READ_INTRUDER_CFG) as attributes.

    The state is the number of settings read.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "panel_settings"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:cog-outline"

    def __init__(self, coordinator: SpcFlexCCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id(coordinator)}_panel_settings"
        self._attr_device_info = build_device_info(coordinator)

    @property
    def available(self) -> bool:
        return bool(self.coordinator.data.intruder_config)

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.intruder_config)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        return {
            **self.coordinator.data.intruder_config,
            "installed_languages": self.coordinator.data.installed_languages,
            # By the web page's names, timers in the web page's units.
            "settings": decode_system_settings(self.coordinator.data.intruder_config),
        }


class SpcPanelSensor(CoordinatorEntity[SpcFlexCCoordinator], SensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: SpcFlexCCoordinator, description: SensorEntityDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id(coordinator)}_{description.key}"
        self._attr_device_info = build_device_info(coordinator)

    @property
    def native_value(self) -> float | int | datetime | None:
        return getattr(self.coordinator.data.panel, self.entity_description.key)


def build_device_info(coordinator: SpcFlexCCoordinator) -> DeviceInfo:
    panel = coordinator.data.panel
    serial = panel.serial_number or coordinator.entry.entry_id
    name = panel.installation_name or "SPC"
    model = f"SPC{panel.spc_variant}" if panel.spc_variant else panel.spc_type or "SPC"
    return DeviceInfo(
        identifiers={(DOMAIN, str(serial))},
        name=name,
        manufacturer="Vanderbilt",
        model=model,
        serial_number=str(serial),
        sw_version=panel.firmware_version,
        hw_version=panel.hardware_version,
        configuration_url=f"http://{coordinator.entry.data[CONF_HOST]}",
    )


def entry_id(coordinator: SpcFlexCCoordinator) -> str:
    return coordinator.entry.entry_id


class SpcAtsActivePathSensor(CoordinatorEntity[SpcFlexCCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: SpcFlexCCoordinator, ats_id: int) -> None:
        super().__init__(coordinator)
        self.ats_id = ats_id
        ats = coordinator.data.ats[ats_id]
        self._attr_translation_key = "ats_active_path"
        self._attr_translation_placeholders = {"ats_name": ats.name or f"ATS {ats_id}"}
        self._attr_unique_id = f"{coordinator.entry.entry_id}_ats_{ats_id}_active_path"
        self._attr_device_info = build_device_info(coordinator)

    @property
    def available(self) -> bool:
        return self.ats_id in self.coordinator.data.ats

    @property
    def native_value(self) -> str | None:
        ats = self.coordinator.data.ats.get(self.ats_id)
        if ats is None:
            return None
        for atp in ats.atps.values():
            if atp.active is True:
                return atp.name or f"ATP {atp.atp_id}"
        return None


class SpcAtpLastTxSensor(CoordinatorEntity[SpcFlexCCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self, coordinator: SpcFlexCCoordinator, ats_id: int, atp_id: int
    ) -> None:
        super().__init__(coordinator)
        self.ats_id = ats_id
        self.atp_id = atp_id
        atp = coordinator.data.ats[ats_id].atps[atp_id]
        self._attr_translation_key = "atp_last_tx_ok"
        self._attr_translation_placeholders = {"atp_name": atp.name or f"ATP {atp_id}"}
        self._attr_unique_id = (
            f"{coordinator.entry.entry_id}_ats_{ats_id}_atp_{atp_id}_last_tx_ok"
        )
        self._attr_device_info = build_device_info(coordinator)

    def _atp(self) -> AtpState | None:
        ats = self.coordinator.data.ats.get(self.ats_id)
        return None if ats is None else ats.atps.get(self.atp_id)

    @property
    def available(self) -> bool:
        return self._atp() is not None

    @property
    def native_value(self) -> datetime | None:
        atp = self._atp()
        return None if atp is None else atp.last_tx_ok_timestamp


class SpcDoorSensorBase(CoordinatorEntity[SpcFlexCCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: SpcFlexCCoordinator, door_id: int) -> None:
        super().__init__(coordinator)
        self.door_id = door_id
        self._attr_translation_placeholders = door_placeholders(coordinator, door_id)
        self._attr_device_info = build_door_device_info(coordinator, door_id)

    def _door(self) -> DoorState | None:
        return self.coordinator.data.doors.get(self.door_id)

    @property
    def available(self) -> bool:
        return self._door() is not None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        door = self._door()
        if door is None:
            return {}
        return {
            "door_id": door.door_id,
            "door_name": door.name or door.zone_name,
            "zone_id": door.zone_id,
            "zone_name": door.zone_name,
            "area_id": door.area_id,
            "area_name": door.area_name,
            "area_side_1": door.area_side_1,
            "area_side_1_name": door.area_side_1_name,
            "area_side_2": door.area_side_2,
            "area_side_2_name": door.area_side_2_name,
            "dps_input": door.dps_input,
            "drs_input": door.drs_input,
            "reader1_format": door.reader1_format,
            "reader2_format": door.reader2_format,
            "entry_exit": door.entry_exit,
            "normal_allowed": door.normal_allowed,
            "lock_allowed": door.lock_allowed,
            "unlock_allowed": door.unlock_allowed,
            "momentary_allowed": door.momentary_allowed,
            "granted_time": door.granted_time,
            "raw_status": door.status,
            "raw_mode": door.mode,
        }


class SpcDoorStatusSensor(SpcDoorSensorBase):
    """DOOR_STATUS STATUS as the panel sends it; its values are not mapped yet.

    The web page's Status column is the door mode (see SpcDoorModeSensor).
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: SpcFlexCCoordinator, door_id: int) -> None:
        super().__init__(coordinator, door_id)
        self._attr_translation_key = "door_status"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_door_{door_id}_status"

    @property
    def native_value(self) -> int | None:
        door = self._door()
        return None if door is None else door.status


# A zone's status in the words of the panel's web page (Status > Inputs):
# isolated and inhibited first, then alarm, tamper, trouble, active input.
# ZONE_STATUS INPUT values, the SPC zone input states. Seen on the owner's
# panel: 0, 1, 3 (zone 36) and 6 (zone 39, which the web page's wireless
# status showed as "Detektor saknas").
ZONE_INPUT_STATES = {
    0: "closed",
    1: "open",
    2: "short",
    3: "disconnected",
    4: "masked",
    5: "dc_substitution",
    6: "missing",
    7: "offline",
}
ZONE_INPUT_FAULTS = (
    "short",
    "disconnected",
    "masked",
    "dc_substitution",
    "missing",
    "offline",
)
ZONE_STATUSES = [
    "normal",
    "active",
    "alarm",
    "tamper",
    "trouble",
    *ZONE_INPUT_FAULTS,
    "inhibited",
    "isolated",
]


def zone_status(zone) -> str | None:
    """Return one status for a zone, like the web page's Status column."""
    if zone.isolated or zone.status == 2:
        return "isolated"
    if zone.inhibited or zone.status == 1:
        return "inhibited"
    if zone.alarm_state not in (None, 0):
        return "alarm"
    input_state = ZONE_INPUT_STATES.get(zone.input_state)  # type: ignore[arg-type]
    if input_state in ZONE_INPUT_FAULTS:
        return input_state
    if zone.event_tamper:
        return "tamper"
    if zone.event_trouble:
        return "trouble"
    if zone.logic_input == 1:
        return "active"
    if zone.logic_input == 0:
        return "normal"
    return None


class SpcZoneStatusSensor(CoordinatorEntity[SpcFlexCCoordinator], SensorEntity):
    """One zone's status like the web page: isolated, inhibited, alarm, an
    input fault (short, disconnected, masked, missing, offline), tamper,
    trouble, active or normal."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ZONE_STATUSES

    def __init__(self, coordinator: SpcFlexCCoordinator, zone_id: int) -> None:
        super().__init__(coordinator)
        self.zone_id = zone_id
        zone = coordinator.data.zones[zone_id]
        self._attr_translation_key = "zone_status"
        self._attr_translation_placeholders = zone_placeholders(zone_id, zone)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_zone_{zone_id}_status"
        self._attr_device_info = build_zone_device_info(coordinator, zone_id)

    @property
    def available(self) -> bool:
        return self.zone_id in self.coordinator.data.zones

    @property
    def native_value(self) -> str | None:
        zone = self.coordinator.data.zones.get(self.zone_id)
        return None if zone is None else zone_status(zone)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        zone = self.coordinator.data.zones.get(self.zone_id)
        if zone is None:
            return {}
        area = (
            self.coordinator.data.areas.get(zone.area_id)
            if zone.area_id is not None
            else None
        )
        area_name = area.name if area is not None else zone.area_name
        return {
            "zone_id": self.zone_id,
            "area": numbered(zone.area_id, area_name, "Area")
            if zone.area_id is not None
            else None,
            "zone_type": SPC_ZONE_TYPES.get(zone.zone_type)
            if zone.zone_type is not None
            else None,
            "input": ZONE_INPUT_STATES.get(zone.input_state)  # type: ignore[arg-type]
            if zone.input_state is not None
            else None,
        }


class SpcUnknownCardsSensor(CoordinatorEntity[SpcFlexCCoordinator], SensorEntity):
    """Cards the panel has seen but does not know, newest first.

    State = how many; ``cards`` has the index for assign_unknown_card, the
    door (reader), card number, when it was last presented and how often.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "unknown_cards"
    _attr_icon = "mdi:card-account-details-outline"

    def __init__(self, coordinator: SpcFlexCCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id(coordinator)}_unknown_cards"
        self._attr_device_info = build_device_info(coordinator)

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.unknown_cards)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        doors = self.coordinator.data.doors
        cards = []
        for card in self.coordinator.data.unknown_cards:
            door_id = str(card.get("door_id") or "")
            door = doors.get(int(door_id)) if door_id.isdigit() else None
            cards.append(
                {
                    "index": card.get("index"),
                    "door": numbered(int(door_id), door.name or door.zone_name, "Door")
                    if door is not None
                    else door_id,
                    "card_number": card.get("card_no"),
                    "last_presented": card.get("last_presented"),
                    "presented_count": card.get("presented_count"),
                }
            )
        return {"cards": cards}


class SpcInhibitedIsolatedSensor(CoordinatorEntity[SpcFlexCCoordinator], SensorEntity):
    """What is inhibited or isolated, like the panel's home page lists it.

    State = how many; ``items`` lists zones, X-BUS faults and system alerts.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "inhibited_isolated"
    _attr_icon = "mdi:shield-off-outline"

    def __init__(self, coordinator: SpcFlexCCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id(coordinator)}_inhibited_isolated"
        self._attr_device_info = build_device_info(coordinator)

    def _items(self) -> list[dict[str, object]]:
        data = self.coordinator.data
        items: list[dict[str, object]] = []
        for zone_id, zone in sorted(data.zones.items()):
            state = zone_status(zone)
            if state in ("inhibited", "isolated"):
                items.append(
                    {
                        "kind": "zone",
                        "id": zone_id,
                        "name": numbered(zone_id, zone.name),
                        "state": state,
                    }
                )
        for serial, device in sorted(data.xbus_devices.items()):
            for state, raw in (
                ("inhibited", device.inhibit_raw),
                ("isolated", device.isolate_raw),
            ):
                try:
                    mask = int(raw or "0", 16)
                except ValueError:
                    continue
                bit = 1
                while bit <= mask:
                    if mask & bit:
                        items.append(
                            {
                                "kind": "xbus",
                                "id": serial,
                                "name": device.name or serial,
                                "fault": XBUS_MASK_BITS.get(bit, f"bit_0x{bit:04X}"),
                                "state": state,
                            }
                        )
                    bit <<= 1
        for key, alert in sorted(data.system_alerts.items()):
            for state in ("inhibited", "isolated"):
                if getattr(alert, state, None):
                    items.append({"kind": "system_alert", "id": key, "state": state})
        return items

    @property
    def native_value(self) -> int:
        return len(self._items())

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        return {"items": self._items()}


# DOOR_STATUS MODE values, verified on an SPC4300 (firmware 3.14.1). The
# panel has three door modes: Normal (locked, cards and codes open it),
# Blocked (the panel says "Dörr låst": cards, codes and the exit button are
# refused) and Unlocked. Momentary open is a command, not a mode. Whether the
# door is closed is the door contact, separate from the mode.
DOOR_MODES = {0: "normal", 1: "blocked", 2: "unlocked"}


class SpcDoorModeSensor(SpcDoorSensorBase):
    _attr_device_class = SensorDeviceClass.ENUM

    def __init__(self, coordinator: SpcFlexCCoordinator, door_id: int) -> None:
        super().__init__(coordinator, door_id)
        self._attr_options = list(DOOR_MODES.values())
        self._attr_translation_key = "door_mode"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_door_{door_id}_mode"

    @property
    def native_value(self) -> str | None:
        """The door mode; an unlisted MODE value stays in `raw_mode`."""
        door = self._door()
        if door is None or door.mode is None:
            return None
        return DOOR_MODES.get(door.mode)


class SpcXBusSensorBase(CoordinatorEntity[SpcFlexCCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: SpcFlexCCoordinator, serial_number: str) -> None:
        super().__init__(coordinator)
        self.serial_number = serial_number
        self._attr_device_info = build_xbus_device_info(coordinator, serial_number)

    @property
    def available(self) -> bool:
        return self.serial_number in self.coordinator.data.xbus_devices


class SpcXBusAuxVoltageSensor(SpcXBusSensorBase):
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_suggested_display_precision = 1
    _attr_translation_key = "xbus_aux_voltage"

    def __init__(self, coordinator: SpcFlexCCoordinator, serial_number: str) -> None:
        super().__init__(coordinator, serial_number)
        self._attr_unique_id = (
            f"{coordinator.entry.entry_id}_xbus_{serial_number}_aux_voltage"
        )

    @property
    def native_value(self) -> float | None:
        device = self.coordinator.data.xbus_devices.get(self.serial_number)
        return None if device is None else device.aux_voltage


class SpcXBusAuxCurrentSensor(SpcXBusSensorBase):
    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.MILLIAMPERE
    _attr_translation_key = "xbus_aux_current"

    def __init__(self, coordinator: SpcFlexCCoordinator, serial_number: str) -> None:
        super().__init__(coordinator, serial_number)
        self._attr_unique_id = (
            f"{coordinator.entry.entry_id}_xbus_{serial_number}_aux_current"
        )

    @property
    def native_value(self) -> float | None:
        device = self.coordinator.data.xbus_devices.get(self.serial_number)
        return None if device is None else device.aux_current


# Power supply of an X-BUS device with its own PSU (e.g. an I/O expander in a
# PSU cabinet), from STATUS_XBUS: field -> (translation key, kind).
XBUS_PSU_FIELDS: dict[str, tuple[str, str]] = {
    "PSU_BATT_VOLT": ("xbus_psu_battery_voltage", "V"),
    "PSU_BATT_CURR": ("xbus_psu_battery_current", "mA"),
    "PSU_OUT1_VOLT": ("xbus_psu_output_1_voltage", "V"),
    "PSU_OUT1_CURR": ("xbus_psu_output_1_current", "mA"),
    "PSU_OUT2_VOLT": ("xbus_psu_output_2_voltage", "V"),
    "PSU_OUT2_CURR": ("xbus_psu_output_2_current", "mA"),
    "PSU_OUT3_VOLT": ("xbus_psu_output_3_voltage", "V"),
    "PSU_OUT3_CURR": ("xbus_psu_output_3_current", "mA"),
}


def _psu_number(raw: object, unit: str) -> float | None:
    text = str(raw or "").strip()
    text = text.removesuffix(unit)
    try:
        return float(text)
    except ValueError:
        return None


class SpcXBusPsuSensor(SpcXBusSensorBase):
    """One voltage or current of an X-BUS device's own power supply."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator: SpcFlexCCoordinator, serial_number: str, field: str
    ) -> None:
        super().__init__(coordinator, serial_number)
        self.field = field
        key, self.unit = XBUS_PSU_FIELDS[field]
        self._attr_translation_key = key
        if self.unit == "V":
            self._attr_device_class = SensorDeviceClass.VOLTAGE
            self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
        else:
            self._attr_device_class = SensorDeviceClass.CURRENT
            self._attr_native_unit_of_measurement = UnitOfElectricCurrent.MILLIAMPERE
        self._attr_unique_id = (
            f"{coordinator.entry.entry_id}_xbus_{serial_number}_{field.lower()}"
        )

    @property
    def native_value(self) -> float | None:
        device = self.coordinator.data.xbus_devices.get(self.serial_number)
        if device is None:
            return None
        return _psu_number(device.raw.get(self.field), self.unit)

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        if self.field != "PSU_BATT_VOLT":
            return None
        device = self.coordinator.data.xbus_devices.get(self.serial_number)
        raw = device.raw if device is not None else {}
        return {
            "psu_type": raw.get("PSU_TYPE"),
            "psu_mode": raw.get("PSU_MODE"),
            "psu_firmware": raw.get("PSU_FW_VERSION"),
        }


XBUS_STATUSES = ["ok", "fault", "inhibited", "isolated"]


def xbus_status(device) -> str | None:
    """One status per X-BUS device like the web page's X-Bus Status column.

    From the device's own masks in STATUS_XBUS: isolated or inhibited first
    (the web page showed "Isolera" for IO Garage while ISOLATE was 000A),
    then an active input or alert as a fault, otherwise OK.
    """
    values = []
    for raw in (
        device.isolate_raw,
        device.inhibit_raw,
        device.input_raw,
        device.alert_raw,
    ):
        try:
            values.append(int(raw or "0", 16))
        except ValueError:
            return None
    isolate, inhibit, inputs, alerts = values
    if isolate:
        return "isolated"
    if inhibit:
        return "inhibited"
    if inputs or alerts:
        return "fault"
    return "ok"


class SpcXBusStatusSensor(SpcXBusSensorBase):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = XBUS_STATUSES
    _attr_translation_key = "xbus_status"

    def __init__(self, coordinator: SpcFlexCCoordinator, serial_number: str) -> None:
        super().__init__(coordinator, serial_number)
        self._attr_unique_id = (
            f"{coordinator.entry.entry_id}_xbus_{serial_number}_status"
        )

    @property
    def native_value(self) -> str | None:
        device = self.coordinator.data.xbus_devices.get(self.serial_number)
        return None if device is None else xbus_status(device)


class SpcXBusDiagnosticSensor(SpcXBusSensorBase):
    _attr_translation_key = "xbus_diagnostics"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: SpcFlexCCoordinator, serial_number: str) -> None:
        super().__init__(coordinator, serial_number)
        self._attr_unique_id = (
            f"{coordinator.entry.entry_id}_xbus_{serial_number}_diagnostics"
        )

    @property
    def native_value(self) -> str | None:
        device = self.coordinator.data.xbus_devices.get(self.serial_number)
        return None if device is None else device.status_raw

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        device = self.coordinator.data.xbus_devices.get(self.serial_number)
        if device is None:
            return {}
        return {
            "xbus_device_id": device.device_id,
            "name": device.name,
            "serial_number": device.serial_number,
            "device_type": device.device_type,
            "hardware_id": device.hardware_id,
            "input_count": device.input_count,
            "output_count": device.output_count,
            "version": device.version,
            "rf_type": device.rf_type,
            "rf_version": device.rf_version,
            "reader_type": device.reader_type,
            "position_1": device.position_1,
            "position_2": device.position_2,
            "psu_type": device.psu_type,
            "sia_address": device.sia_address,
            "status_raw": device.status_raw,
            "input_raw": device.input_raw,
            "alert_raw": device.alert_raw,
            "inhibit_raw": device.inhibit_raw,
            "isolate_raw": device.isolate_raw,
        }


class SpcXBusInventorySensor(SpcXBusSensorBase):
    """Expose a small validated X-BUS inventory field."""

    def __init__(
        self,
        coordinator: SpcFlexCCoordinator,
        serial_number: str,
        field: str,
        *,
        diagnostic: bool = False,
    ) -> None:
        super().__init__(coordinator, serial_number)
        self.field = field
        self._attr_translation_key = f"xbus_{field}"
        self._attr_unique_id = (
            f"{coordinator.entry.entry_id}_xbus_{serial_number}_{field}"
        )
        if diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> int | None:
        device = self.coordinator.data.xbus_devices.get(self.serial_number)
        return None if device is None else getattr(device, self.field)
