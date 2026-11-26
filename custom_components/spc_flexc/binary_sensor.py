"""Binary sensor entities for the SPC FlexC integration."""

import asyncio
import re
from datetime import UTC, datetime

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    SPC_ZONE_TYPES,
    XBUS_TAMPER_INHIBIT_MASK,
    XBUS_TAMPER_INPUT_MASK,
    XBUS_TAMPER_ISOLATE_MASK,
)
from .coordinator import SpcFlexCCoordinator
from .entity_ids import with_spc_entity_ids
from .flexc.device import (
    build_door_device_info,
    build_panel_device_info,
    build_xbus_device_info,
    build_zone_device_info,
    door_placeholders,
    migrate_xbus_registry_identity,
    zone_input,
    zone_placeholders,
)
from .flexc.panel_status import SYSTEM_ALERTS

ZONE_ACTIVITY_PULSE_SECONDS = 2.0

PANEL = (
    BinarySensorEntityDescription(
        key="internal_bells", translation_key="internal_bells"
    ),
    BinarySensorEntityDescription(
        key="external_bells", translation_key="external_bells"
    ),
    BinarySensorEntityDescription(key="engineer_mode", translation_key="engineer_mode"),
)

FAULTS = (
    BinarySensorEntityDescription(key="mains_fault", translation_key="mains_fault"),
    BinarySensorEntityDescription(key="battery_fault", translation_key="battery_fault"),
    BinarySensorEntityDescription(key="panel_tamper", translation_key="panel_tamper"),
    BinarySensorEntityDescription(key="modem_1_fault", translation_key="modem_1_fault"),
    BinarySensorEntityDescription(
        key="modem_1_line_fault", translation_key="modem_1_line_fault"
    ),
    BinarySensorEntityDescription(key="rf_jamming", translation_key="rf_jamming"),
    BinarySensorEntityDescription(
        key="xbus_mains_fault", translation_key="xbus_mains_fault"
    ),
    BinarySensorEntityDescription(
        key="xbus_battery_fault", translation_key="xbus_battery_fault"
    ),
)


# Panel faults that FlexC events report, and the system alert of
# CMD_STATUS_PANEL that reports the same thing. When the panel answers
# CMD_STATUS_PANEL, the system alert is the only entity for it (it has the
# current state from start-up); the event-only entity is created only on
# panels without CMD_STATUS_PANEL.
PANEL_ALERT_FALLBACK: dict[str, str] = {
    "mains_fault": "mains_fault",
    "battery_fault": "battery_fault",
    "panel_tamper": "cabinet_tamper",
}


class SpcBinary(CoordinatorEntity, BinarySensorEntity):
    """Represent a standard SPC binary state."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True

    def __init__(self, coordinator, description, section):
        super().__init__(coordinator)
        self.entity_description = description
        self.section = section
        if section == "faults":
            self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{description.key}"
        self._attr_device_info = build_panel_device_info(coordinator)

    @property
    def is_on(self) -> bool | None:
        """Return the binary sensor state."""
        section = getattr(self.coordinator.data, self.section)
        return getattr(section, self.entity_description.key)


class SpcAtpFaultSensor(CoordinatorEntity[SpcFlexCCoordinator], BinarySensorEntity):
    """Represent the last known FlexC ATP fault state."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: SpcFlexCCoordinator, ats_id: int, atp_id: int
    ) -> None:
        super().__init__(coordinator)
        self.ats_id = ats_id
        self.atp_id = atp_id
        atp = coordinator.data.ats[ats_id].atps[atp_id]
        self._attr_translation_key = "atp_fault"
        self._attr_translation_placeholders = {"atp_name": atp.name or f"ATP {atp_id}"}
        self._attr_unique_id = (
            f"{coordinator.entry.entry_id}_ats_{ats_id}_atp_{atp_id}_fault"
        )
        self._attr_device_info = build_panel_device_info(coordinator)

    @property
    def is_on(self) -> bool | None:
        ats = self.coordinator.data.ats.get(self.ats_id)
        if ats is None:
            return None
        atp = ats.atps.get(self.atp_id)
        return None if atp is None else atp.fault

    @property
    def available(self) -> bool:
        ats = self.coordinator.data.ats.get(self.ats_id)
        return ats is not None and self.atp_id in ats.atps


class SpcFlexCConnectionSensor(
    CoordinatorEntity[SpcFlexCCoordinator], BinarySensorEntity
):
    """FlexC connection availability."""

    _attr_translation_key = "flexc_connection"
    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: SpcFlexCCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_flexc_connection"
        self._attr_device_info = build_panel_device_info(coordinator)

    @property
    def is_on(self) -> bool:
        return bool(
            self.coordinator.last_update_success and self.coordinator.client.connected
        )


# Zone types that say what the detector is.
_ZONE_TYPE_DEVICE_CLASS: dict[int, BinarySensorDeviceClass] = {
    3: BinarySensorDeviceClass.SMOKE,  # fire
    4: BinarySensorDeviceClass.DOOR,  # emergency exit
    8: BinarySensorDeviceClass.TAMPER,
    15: BinarySensorDeviceClass.PROBLEM,  # detector fault
    17: BinarySensorDeviceClass.VIBRATION,  # seismic
    19: BinarySensorDeviceClass.PROBLEM,  # hold-up fault
    20: BinarySensorDeviceClass.PROBLEM,  # warning fault
    23: BinarySensorDeviceClass.VIBRATION,  # glass break
    24: BinarySensorDeviceClass.MOISTURE,  # water
    25: BinarySensorDeviceClass.HEAT,
    27: BinarySensorDeviceClass.GAS,
    29: BinarySensorDeviceClass.CO,
}

# Otherwise a zone type is the alarm function (alarm, entry/exit, ...), not
# the kind of detector, so the zone name is tried first: English, Swedish and
# French words, as stems because the panel cuts names at 16 characters
# ("Vardagsrumsfönst"). The first match wins. Idea and English words from
# henrikekblad/spc-flexc-home-assistant (docs/zones.md).
_ZONE_NAME_DEVICE_CLASS: tuple[tuple[re.Pattern[str], BinarySensorDeviceClass], ...] = (
    (
        re.compile(r"\bpir\b|motion|rörelse|mouvement", re.IGNORECASE),
        BinarySensorDeviceClass.MOTION,
    ),
    (
        re.compile(r"glass|glaskross|bris de glace", re.IGNORECASE),
        BinarySensorDeviceClass.VIBRATION,
    ),
    (
        re.compile(r"window|fönst|fenêtre|fenetre", re.IGNORECASE),
        BinarySensorDeviceClass.WINDOW,
    ),
    (
        re.compile(r"garage ?door|garageport|porte (de )?garage", re.IGNORECASE),
        BinarySensorDeviceClass.GARAGE_DOOR,
    ),
    (
        re.compile(r"door|gate|dörr|\bport\b|grind|\bporte\b|portail", re.IGNORECASE),
        BinarySensorDeviceClass.DOOR,
    ),
    (
        re.compile(r"smoke|\brök|fumée|fumee", re.IGNORECASE),
        BinarySensorDeviceClass.SMOKE,
    ),
    (
        re.compile(r"water|leak|vatten|läck|fuite", re.IGNORECASE),
        BinarySensorDeviceClass.MOISTURE,
    ),
    (
        re.compile(r"tamper|sabotage|autoprotection", re.IGNORECASE),
        BinarySensorDeviceClass.TAMPER,
    ),
)

# Without a type or a word that says it: what the alarm function usually is.
_ZONE_TYPE_FALLBACK: dict[int, BinarySensorDeviceClass] = {
    0: BinarySensorDeviceClass.MOTION,  # alarm
    1: BinarySensorDeviceClass.OPENING,  # entry/exit
    2: BinarySensorDeviceClass.MOTION,  # exit terminator
    30: BinarySensorDeviceClass.OPENING,  # entry/exit 2
}


def zone_device_class(
    zone_type: int | None, name: str | None = None
) -> BinarySensorDeviceClass | None:
    """Return the Home Assistant device class for an SPC zone.

    The zone type decides when it says what the detector is (fire, glass
    break, water, ...). Otherwise a word in the zone name decides, and
    otherwise the usual detector for the zone's alarm function. A device
    class the user sets in Home Assistant always wins over this.
    """
    if zone_type in _ZONE_TYPE_DEVICE_CLASS:
        return _ZONE_TYPE_DEVICE_CLASS[zone_type]
    if name:
        for pattern, device_class in _ZONE_NAME_DEVICE_CLASS:
            if pattern.search(name):
                return device_class
    if zone_type is None:
        return None
    return _ZONE_TYPE_FALLBACK.get(zone_type)


class SpcZoneDiagnosticBinarySensor(
    CoordinatorEntity[SpcFlexCCoordinator], BinarySensorEntity
):
    """Zone alarm diagnostics independent from the physical zone input."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: SpcFlexCCoordinator, zone_id: int, kind: str
    ) -> None:
        super().__init__(coordinator)
        self.zone_id = zone_id
        self.kind = kind
        zone = coordinator.data.zones[zone_id]
        self._attr_translation_key = f"zone_{kind}"
        self._attr_translation_placeholders = zone_placeholders(zone_id, zone)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_zone_{zone_id}_{kind}"
        self._attr_device_class = (
            BinarySensorDeviceClass.TAMPER
            if kind == "tamper"
            else BinarySensorDeviceClass.PROBLEM
        )
        self._attr_device_info = build_zone_device_info(coordinator, zone_id)

    @property
    def is_on(self) -> bool | None:
        zone = self.coordinator.data.zones.get(self.zone_id)
        if zone is None:
            return None
        return zone.event_tamper if self.kind == "tamper" else zone.event_trouble

    @property
    def available(self) -> bool:
        return self.zone_id in self.coordinator.data.zones

    @property
    def extra_state_attributes(self) -> dict:
        zone = self.coordinator.data.zones.get(self.zone_id)
        return {
            "zone_id": self.zone_id,
            "area_id": zone.area_id if zone else None,
            "diagnostic_kind": self.kind,
        }


class SpcZoneBinarySensor(CoordinatorEntity[SpcFlexCCoordinator], BinarySensorEntity):
    """Represent the live state of an SPC zone."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SpcFlexCCoordinator, zone_id: int) -> None:
        super().__init__(coordinator)
        self.zone_id = zone_id
        self._activity_pulse_active = False
        self._activity_pulse_handle: asyncio.TimerHandle | None = None
        self._last_actuations: int | None = None
        zone = coordinator.data.zones[zone_id]
        self._attr_device_class = zone_device_class(zone.zone_type, zone.name)
        self._attr_translation_key = "zone"
        self._attr_translation_placeholders = zone_placeholders(zone_id, zone)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_zone_{zone_id}_motion"
        self._attr_device_info = build_zone_device_info(coordinator, zone_id)

    @property
    def is_on(self) -> bool | None:
        zone = self.coordinator.data.zones.get(self.zone_id)
        if zone is None:
            return None
        # FlexC LOGIC_INPUT is not boolean: 3 denotes a disconnected input
        # on a tampered zone, not PIR motion. Unknown values must not be
        # reported as movement until their meaning is validated.
        if zone.logic_input == 1:
            return True
        if zone.logic_input == 0:
            return self._activity_pulse_active
        if zone.logic_input == 3 and zone.event_tamper is True:
            return False
        return None

    @property
    def available(self) -> bool:
        return self.zone_id in self.coordinator.data.zones

    @property
    def extra_state_attributes(self) -> dict:
        zone = self.coordinator.data.zones.get(self.zone_id)
        if zone is None:
            return {}
        area = (
            self.coordinator.data.areas.get(zone.area_id)
            if zone.area_id is not None
            else None
        )
        intrusion_active = (
            zone.zone_id in area.active_alarm_zones if area is not None else False
        )
        intrusion_triggered = (
            zone.zone_id in area.triggered_alarm_zones if area is not None else False
        )
        return {
            "zone_id": zone.zone_id,
            "zone_name": zone.name,
            "area_id": zone.area_id,
            "area_name": area.name if area is not None else zone.area_name,
            "intrusion_active": intrusion_active,
            "intrusion_triggered": intrusion_triggered,
            "spc_zone_type": SPC_ZONE_TYPES.get(zone.zone_type)
            if zone.zone_type is not None
            else None,
            "logic_input": zone.logic_input,
            "status": zone.status,
            "proc_state": zone.proc_state,
            "alarm_state": zone.alarm_state,
            "inhibited": zone.inhibited,
            "isolated": zone.isolated,
            "actuations_since_last_read": zone.actuations_since_last_read,
            "event_tamper": zone.event_tamper,
            "event_trouble": zone.event_trouble,
            "last_event": zone.last_event,
            "input_state": zone.input_state,
            **zone_input(self.coordinator, zone.zone_id),
        }

    def _handle_coordinator_update(self) -> None:
        zone = self.coordinator.data.zones.get(self.zone_id)
        if zone is not None:
            actuations = zone.actuations_since_last_read
            # The counter is a fallback for motion missed by polling, not a
            # second activation after a live 2100/2101 event. A repeated
            # coordinator update must never replay the same counter value.
            has_live_events = (
                self.coordinator._pir_event_generation.get(self.zone_id, 0) > 0
            )
            if has_live_events or zone.logic_input != 0:
                if self._activity_pulse_handle is not None:
                    self._activity_pulse_handle.cancel()
                    self._activity_pulse_handle = None
                self._activity_pulse_active = False
            elif (
                self._attr_device_class == BinarySensorDeviceClass.MOTION
                and actuations is not None
                and actuations > 0
                and actuations != self._last_actuations
            ):
                self._start_activity_pulse()
            self._last_actuations = actuations
        super()._handle_coordinator_update()

    def _start_activity_pulse(self) -> None:
        self._activity_pulse_active = True
        if self._activity_pulse_handle is not None:
            self._activity_pulse_handle.cancel()
        self._activity_pulse_handle = asyncio.get_running_loop().call_later(
            ZONE_ACTIVITY_PULSE_SECONDS, self._end_activity_pulse
        )

    def _end_activity_pulse(self) -> None:
        self._activity_pulse_handle = None
        self._activity_pulse_active = False
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        if self._activity_pulse_handle is not None:
            self._activity_pulse_handle.cancel()
            self._activity_pulse_handle = None
        await super().async_will_remove_from_hass()


def _xbus_mask_state(raw_value: str | None, mask: int) -> bool | None:
    """Return a validated X-BUS bit state from a hexadecimal status field."""
    if raw_value is None:
        return None
    try:
        return bool(int(raw_value, 16) & mask)
    except ValueError:
        return None


class SpcXBusDeviceBinarySensor(
    CoordinatorEntity[SpcFlexCCoordinator], BinarySensorEntity
):
    """Represent a validated X-BUS tamper state."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: SpcFlexCCoordinator, serial_number: str, state_key: str
    ) -> None:
        super().__init__(coordinator)
        self.serial_number = serial_number
        self.state_key = state_key
        self._attr_translation_key = f"xbus_{state_key}"
        if state_key == "tamper_fault":
            self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_unique_id = (
            f"{coordinator.entry.entry_id}_xbus_{serial_number}_{state_key}"
        )
        self._attr_device_info = build_xbus_device_info(coordinator, serial_number)

    @property
    def is_on(self) -> bool | None:
        device = self.coordinator.data.xbus_devices.get(self.serial_number)
        if device is None:
            return None
        event_state = getattr(device, self.state_key)
        if event_state is not None:
            return event_state
        if self.state_key == "tamper_fault":
            return _xbus_mask_state(device.input_raw, XBUS_TAMPER_INPUT_MASK)
        if self.state_key == "tamper_inhibited":
            return _xbus_mask_state(device.inhibit_raw, XBUS_TAMPER_INHIBIT_MASK)
        if self.state_key == "tamper_isolated":
            return _xbus_mask_state(device.isolate_raw, XBUS_TAMPER_ISOLATE_MASK)
        return None

    @property
    def available(self) -> bool:
        return self.serial_number in self.coordinator.data.xbus_devices

    @property
    def extra_state_attributes(self) -> dict:
        device = self.coordinator.data.xbus_devices.get(self.serial_number)
        if device is None:
            return {}
        return {
            "xbus_device_id": device.device_id,
            "xbus_device_name": device.name,
            "serial_number": device.serial_number,
            "device_type": device.device_type,
            "hardware_id": device.hardware_id,
            "version": device.version,
            "status_raw": device.status_raw,
            "aux_voltage": device.aux_voltage,
            "aux_current": device.aux_current,
            "input_raw": device.input_raw,
            "alert_raw": device.alert_raw,
            "inhibit_raw": device.inhibit_raw,
            "isolate_raw": device.isolate_raw,
            "sia_address": device.sia_address,
            "tamper_fault": device.tamper_fault,
            "tamper_inhibited": _xbus_mask_state(
                device.inhibit_raw, XBUS_TAMPER_INHIBIT_MASK
            ),
            "tamper_isolated": device.tamper_isolated,
            "last_event": device.last_event,
        }


class SpcSystemAlertSensor(CoordinatorEntity[SpcFlexCCoordinator], BinarySensorEntity):
    """One panel system alert from the CMD_STATUS_PANEL SYSALERT masks.

    On while the fault is present or the alert is raised. The attributes say
    whether it is inhibited or isolated and whether that is allowed.
    """

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: SpcFlexCCoordinator, key: str, alert_id: int
    ) -> None:
        super().__init__(coordinator)
        self.key = key
        self.alert_id = alert_id
        self._attr_translation_key = f"system_alert_{key}"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_system_alert_{key}"
        self._attr_device_info = build_panel_device_info(coordinator)

    def _state(self):
        return self.coordinator.data.system_alerts.get(self.key)

    @property
    def available(self) -> bool:
        return self._state() is not None

    @property
    def is_on(self) -> bool | None:
        state = self._state()
        return None if state is None else state.active or state.alerted

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        state = self._state()
        if state is None:
            return {}
        return {
            "alert_id": self.alert_id,
            "fault_present": state.active,
            "alert_raised": state.alerted,
            "inhibited": state.inhibited,
            "isolated": state.isolated,
            "inhibit_allowed": state.inhibit_allowed,
            "isolate_allowed": state.isolate_allowed,
        }


class SpcEthernetSensor(CoordinatorEntity[SpcFlexCCoordinator], BinarySensorEntity):
    """Panel Ethernet link (ETHERNETINFO STATE) from CMD_STATUS_PANEL."""

    _attr_has_entity_name = True
    _attr_translation_key = "ethernet"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: SpcFlexCCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_ethernet"
        self._attr_device_info = build_panel_device_info(coordinator)

    @property
    def available(self) -> bool:
        return bool(self.coordinator.data.ethernet)

    @property
    def is_on(self) -> bool | None:
        state = self.coordinator.data.ethernet.get("STATE")
        return None if state is None else state == "1"

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        ethernet = self.coordinator.data.ethernet
        return {
            "dhcp": ethernet.get("DHCP_ENABLED") == "1" if ethernet else None,
            "ip_address": ethernet.get("IP_ADDRESS"),
            "netmask": ethernet.get("NETMASK"),
            "gateway": ethernet.get("GATEWAY"),
        }


class SpcDoorBinarySensorBase(
    CoordinatorEntity[SpcFlexCCoordinator], BinarySensorEntity
):
    """Common base for binary sensors that belong to one SPC door."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: SpcFlexCCoordinator, door_id: int, key: str
    ) -> None:
        super().__init__(coordinator)
        self.door_id = door_id
        self._attr_translation_key = key
        self._attr_translation_placeholders = door_placeholders(coordinator, door_id)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_door_{door_id}_{key}"
        self._attr_device_info = build_door_device_info(coordinator, door_id)

    def _door(self):
        return self.coordinator.data.doors.get(self.door_id)

    @property
    def available(self) -> bool:
        return self._door() is not None


class SpcDoorEntryGrantedSensor(SpcDoorBinarySensorBase):
    """On while the door's lock relay is energised after Entry Granted (3000).

    FlexC does not report the relay itself. The state is derived from event
    3000 for this door and the door's GRANTED_TIME from GET_DOOR_CONFIG.
    """

    def __init__(self, coordinator: SpcFlexCCoordinator, door_id: int) -> None:
        super().__init__(coordinator, door_id, "door_entry_granted")

    @property
    def is_on(self) -> bool | None:
        door = self._door()
        if door is None:
            return None
        until = door.entry_granted_until
        return until is not None and datetime.now(UTC) < until

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        door = self._door()
        if door is None:
            return {}
        return {
            "last_entry_granted": None
            if door.entry_granted_at is None
            else door.entry_granted_at.isoformat(),
            "granted_time": door.granted_time,
            # Last unlock (granted, exit granted, exit button; who) and last
            # opening of the door, kept across restarts (owner 2026-11-14:
            # an unlock is not a passage; a passage is the door opening).
            **self.coordinator.door_history(self.door_id),
        }


class SpcDoorOpenSensor(SpcDoorBinarySensorBase):
    """Door position (DPS input): on when the door is open."""

    _attr_device_class = BinarySensorDeviceClass.DOOR

    def __init__(self, coordinator: SpcFlexCCoordinator, door_id: int) -> None:
        super().__init__(coordinator, door_id, "door_open")

    @property
    def is_on(self) -> bool | None:
        door = self._door()
        if door is None:
            return None
        return door.door_is_open


class SpcDoorExitButtonSensor(SpcDoorBinarySensorBase):
    """Request-to-exit input (DRS), the web page's "DRS Öppnaknapp" column.

    On while the button is pressed, shown as Normal / Aktiv (owner
    2026-11-14). ``DRS_INPUT`` is the contact (1 open), which the web page
    shows as "DRS Öppnaknapp Öppen/Stängd"; pressed means the contact differs
    from its rest state, given by the button type (normally open or closed)
    in the door configuration. Garageport's button is normally open, so
    "Öppen" there is Normal. The contact is kept as the ``contact`` attribute.
    """

    def __init__(self, coordinator: SpcFlexCCoordinator, door_id: int) -> None:
        super().__init__(coordinator, door_id, "door_exit_button")

    @property
    def is_on(self) -> bool | None:
        door = self._door()
        if door is None:
            return None
        return door.exit_button_pressed

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        door = self._door()
        if door is None:
            return {}
        return {
            "contact": None
            if door.drs_input is None
            else ("open" if door.drs_input else "closed"),
            "pressed": door.exit_button_pressed,
            "normally_open": door.drs_normally_open,
            "ignored": door.drs_ignored,
        }


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up SPC FlexC binary sensors."""
    async_add_entities = with_spc_entity_ids(
        "binary_sensor", entry.entry_id, async_add_entities
    )
    coordinator: SpcFlexCCoordinator = entry.runtime_data
    async_add_entities(
        [SpcBinary(coordinator, description, "panel") for description in PANEL]
        + [
            SpcBinary(coordinator, description, "faults")
            for description in FAULTS
            if description.key not in PANEL_ALERT_FALLBACK
        ]
        + [SpcFlexCConnectionSensor(coordinator)]
    )
    known_atps: set[tuple[int, int]] = set()
    known_zones: set[int] = set()
    known_xbus_entities: set[tuple[str, str]] = set()
    known_doors: set[int] = set()
    known_system_alerts: set[str] = set()
    ethernet_added = False
    panel_faults_resolved: set[str] = set()

    def resolve_panel_faults(entities: list[BinarySensorEntity]) -> None:
        """Use the system alert where the panel has it, else the event entity."""
        alerts = coordinator.data.system_alerts
        unsupported = getattr(coordinator, "_panel_status_unsupported", False) is True
        if not alerts and not unsupported:
            return  # CMD_STATUS_PANEL not read yet
        registry = er.async_get(hass)
        for description in FAULTS:
            key = description.key
            alert_key = PANEL_ALERT_FALLBACK.get(key)
            if alert_key is None or key in panel_faults_resolved:
                continue
            panel_faults_resolved.add(key)
            if alert_key in alerts:
                entity_id = registry.async_get_entity_id(
                    "binary_sensor", DOMAIN, f"{entry.entry_id}_{key}"
                )
                if entity_id is not None:
                    registry.async_remove(entity_id)
            else:
                entities.append(SpcBinary(coordinator, description, "faults"))

    def add_panel_status_entities() -> None:
        nonlocal ethernet_added
        entities: list[BinarySensorEntity] = []
        resolve_panel_faults(entities)
        for alert in SYSTEM_ALERTS:
            if (
                alert.key in coordinator.data.system_alerts
                and alert.key not in known_system_alerts
            ):
                known_system_alerts.add(alert.key)
                entities.append(
                    SpcSystemAlertSensor(coordinator, alert.key, alert.alert_id)
                )
        if coordinator.data.ethernet and not ethernet_added:
            ethernet_added = True
            entities.append(SpcEthernetSensor(coordinator))
        if entities:
            async_add_entities(entities)

    def add_door_entities() -> None:
        entities: list[BinarySensorEntity] = []
        for door_id in coordinator.data.doors:
            if door_id in known_doors:
                continue
            known_doors.add(door_id)
            entities.append(SpcDoorEntryGrantedSensor(coordinator, door_id))
            entities.append(SpcDoorOpenSensor(coordinator, door_id))
            entities.append(SpcDoorExitButtonSensor(coordinator, door_id))
        if entities:
            async_add_entities(entities)

    def add_zone_entities() -> None:
        entities: list[BinarySensorEntity] = []
        for zone_id in coordinator.data.zones:
            if zone_id in known_zones:
                continue
            known_zones.add(zone_id)
            entities.append(SpcZoneBinarySensor(coordinator, zone_id))
            entities.append(
                SpcZoneDiagnosticBinarySensor(coordinator, zone_id, "tamper")
            )
            entities.append(
                SpcZoneDiagnosticBinarySensor(coordinator, zone_id, "trouble")
            )
        if entities:
            async_add_entities(entities)

    def add_atp_entities() -> None:
        entities: list[BinarySensorEntity] = []
        for ats_id, ats in coordinator.data.ats.items():
            for atp_id in ats.atps:
                key = (ats_id, atp_id)
                if key in known_atps:
                    continue
                known_atps.add(key)
                entities.append(SpcAtpFaultSensor(coordinator, ats_id, atp_id))
        if entities:
            async_add_entities(entities)

    def add_xbus_entities() -> None:
        entities: list[BinarySensorEntity] = []
        for serial_number in coordinator.data.xbus_devices:
            for state_key in ("tamper_fault", "tamper_inhibited", "tamper_isolated"):
                key = (serial_number, state_key)
                if key in known_xbus_entities:
                    continue
                known_xbus_entities.add(key)
                migrate_xbus_registry_identity(
                    coordinator, serial_number, "binary_sensor", state_key
                )
                entities.append(
                    SpcXBusDeviceBinarySensor(coordinator, serial_number, state_key)
                )
        if entities:
            async_add_entities(entities)

    add_atp_entities()
    add_zone_entities()
    add_xbus_entities()
    add_door_entities()
    add_panel_status_entities()

    def coordinator_updated() -> None:
        add_atp_entities()
        add_zone_entities()
        add_xbus_entities()
        add_door_entities()
        add_panel_status_entities()

    entry.async_on_unload(coordinator.async_add_listener(coordinator_updated))
