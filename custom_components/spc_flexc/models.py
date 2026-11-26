"""State models for the SPC FlexC integration."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AreaState:
    """Last known SPC area state."""

    area_id: int
    name: str | None = None
    mode: int | None = None
    partset_a_enabled: bool | None = None
    partset_b_enabled: bool | None = None
    last_set_time: datetime | None = None
    last_set_user_id: int | None = None
    last_set_user_name: str | None = None
    last_unset_time: datetime | None = None
    last_unset_user_id: int | None = None
    last_unset_user_name: str | None = None
    # Event history, including partial arm, distinct from SPC status fields.
    last_arm_time: datetime | None = None
    last_arm_user_id: int | None = None
    last_arm_user_name: str | None = None
    last_arm_user_display_name: str | None = None
    last_disarm_time: datetime | None = None
    last_disarm_user_id: int | None = None
    last_disarm_user_name: str | None = None
    last_disarm_user_display_name: str | None = None
    last_alarm: datetime | None = None
    internal_bells: bool | None = None
    external_bells: bool | None = None
    active_alarm_zones: set[int] = field(default_factory=set)
    triggered_alarm_zones: set[int] = field(default_factory=set)
    alarm_event_active: bool = False
    raw: dict[str, Any] = field(default_factory=dict)
    updated_at: datetime | None = None


@dataclass
class AtpState:
    """Last known FlexC ATP state."""

    atp_id: int
    name: str | None = None
    # ATP_SEQ_ID: the ATP's position in its ATS, used by ATP log and test commands.
    seq_id: int | None = None
    uid: int | None = None
    status: int | None = None
    state: int | None = None
    connect_state: int | None = None
    last_tx_ok_timestamp: datetime | None = None

    @property
    def fault(self) -> bool | None:
        """Return the validated ATP fault state."""
        if self.status is None:
            return None
        if self.status == 1:
            return False
        if self.status == 2:
            return True
        return None

    @property
    def active(self) -> bool | None:
        """Return whether this ATP is an active/connected path."""
        if self.connect_state is None:
            return None
        if self.connect_state in (15, 16):
            return True
        if self.connect_state == 0:
            return False
        return None


@dataclass
class AtsState:
    """Last known FlexC ATS state."""

    ats_id: int
    name: str | None = None
    status: int | None = None
    state: int | None = None
    registration_id: str | None = None
    event_log_count: int | None = None
    atps: dict[int, AtpState] = field(default_factory=dict)
    updated_at: datetime | None = None


@dataclass
class PanelState:
    """Current SPC panel state."""

    battery_voltage: float | None = None
    aux_voltage: float | None = None
    aux_current: float | None = None
    ac_frequency: float | None = None
    rf_type: int | None = None
    rf_version: str | None = None
    internal_bells: bool | None = None
    external_bells: bool | None = None
    engineer_mode: bool | None = None
    installation_name: str | None = None
    spc_type: str | None = None
    spc_variant: str | None = None
    serial_number: str | None = None
    firmware_version: str | None = None
    hardware_version: str | None = None
    # SPC_TIME, and SPC_TIME minus Home Assistant's time when it was read.
    panel_time: datetime | None = None
    clock_offset: int | None = None
    # When the system configuration (TIME_SYSCFG) and users (TIME_USERS) last changed.
    configuration_changed: datetime | None = None
    users_changed: datetime | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    updated_at: datetime | None = None


@dataclass
class FaultState:
    """Faults obtained from FlexC events or dedicated status commands."""

    mains_fault: bool | None = None
    battery_fault: bool | None = None
    panel_tamper: bool | None = None
    modem_1_fault: bool | None = None
    modem_1_line_fault: bool | None = None
    modem_2_fault: bool | None = None
    modem_2_line_fault: bool | None = None
    rf_jamming: bool | None = None
    xbus_mains_fault: bool | None = None
    xbus_battery_fault: bool | None = None
    last_event: dict[str, Any] | None = None


@dataclass
class ZoneState:
    """Last known SPC zone state."""

    zone_id: int
    name: str | None = None
    area_id: int | None = None
    area_name: str | None = None
    zone_type: int | None = None
    input_state: int | None = None
    logic_input: int | None = None
    status: int | None = None
    proc_state: int | None = None
    alarm_state: int | None = None
    event_tamper: bool | None = None
    event_trouble: bool | None = None
    last_event: dict[str, Any] | None = None
    inhibit_allowed: bool | None = None
    isolate_allowed: bool | None = None
    restore_allowed: bool | None = None
    actuations_since_last_read: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    updated_at: datetime | None = None

    @property
    def inhibited(self) -> bool | None:
        """Return the explicit FlexC inhibition state when it can be inferred."""
        value = self.raw.get("INHIBITED")
        if value == "1":
            return True
        if value == "0":
            return False
        if "INHIBIT_ALLOWED" in self.raw:
            return False
        return None

    @property
    def deinhibit_allowed(self) -> bool | None:
        """Return whether FlexC currently permits de-inhibiting this zone."""
        value = self.raw.get("DEINHIBIT_ALLOWED")
        if value == "1":
            return True
        if value == "0":
            return False
        if self.inhibited is False:
            return False
        return None

    @property
    def isolated(self) -> bool | None:
        """Return the explicit FlexC isolation state when it can be inferred."""
        value = self.raw.get("ISOLATED")
        if value == "1":
            return True
        if value == "0":
            return False
        if "ISOLATE_ALLOWED" in self.raw:
            return False
        return None

    @property
    def deisolate_allowed(self) -> bool | None:
        """Return whether FlexC currently permits de-isolating this zone."""
        value = self.raw.get("DEISOLATE_ALLOWED")
        if value == "1":
            return True
        if value == "0":
            return False
        if self.isolated is False:
            return False
        return None


@dataclass
class DoorState:
    """Last known SPC access-control door state."""

    door_id: int
    name: str | None = None
    status: int | None = None
    mode: int | None = None
    dps_input: int | None = None
    drs_input: int | None = None
    reader1_format: int | None = None
    reader2_format: int | None = None
    zone_id: int | None = None
    zone_name: str | None = None
    area_id: int | None = None
    area_name: str | None = None
    area_side_1: int | None = None
    area_side_1_name: str | None = None
    area_side_2: int | None = None
    area_side_2_name: str | None = None
    entry_exit: bool | None = None
    normal_allowed: bool | None = None
    lock_allowed: bool | None = None
    unlock_allowed: bool | None = None
    momentary_allowed: bool | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    updated_at: datetime | None = None
    # From GET_DOOR_CONFIG; seconds the lock relay stays energised.
    granted_time: int | None = None
    # From GET_DOOR_CONFIG DOOR_SIDE_0 / DOOR_SIDE_1: the areas on the entry
    # and exit reader's side as the web page shows them (0 = none). None
    # until the configuration is read. DOOR_STATUS reports these one higher
    # (2026-11-13), so the configured values win.
    config_side_entry: int | None = None
    config_side_exit: int | None = None
    # From GET_DOOR_CONFIG ATTRIB (checked 2026-11-13): whether the door
    # contact (DPS, 0x0800) and the exit button (DRS, 0x1000) are normally
    # open, and whether the exit button is ignored (0x00800000). DPS_INPUT
    # and DRS_INPUT are the contact's state (1 open), as the web page shows
    # it ("DRS Öppnaknapp Öppen"); what it means depends on these.
    dps_normally_open: bool | None = None
    drs_normally_open: bool | None = None
    drs_ignored: bool | None = None

    @property
    def door_is_open(self) -> bool | None:
        """Whether the door is open, from DPS_INPUT and the contact type."""
        if self.dps_input is None:
            return None
        return (self.dps_input != 0) != bool(self.dps_normally_open)

    @property
    def exit_button_pressed(self) -> bool | None:
        """Whether the exit button is pressed, from DRS_INPUT and its type.

        None until the door configuration is read or when the panel ignores
        the button.
        """
        if self.drs_input is None or self.drs_normally_open is None or self.drs_ignored:
            return None
        return (self.drs_input != 0) != self.drs_normally_open

    # Event-driven state: last Entry Granted (EV_ID 3000) for this door.
    entry_granted_at: datetime | None = None
    entry_granted_until: datetime | None = None


@dataclass
class MappingGateState:
    """Last known SPC Mapping Gate state."""

    mg_id: int
    name: str | None = None
    state: bool | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    updated_at: datetime | None = None


@dataclass
class XBusDeviceState:
    """Last known X-BUS device state."""

    device_id: int
    name: str | None = None
    serial_number: str | None = None
    device_type: int | None = None
    hardware_id: int | None = None
    input_count: int | None = None
    output_count: int | None = None
    version: str | None = None
    rf_type: int | None = None
    rf_version: str | None = None
    reader_type: int | None = None
    status_raw: str | None = None
    position_1: int | None = None
    position_2: int | None = None
    psu_type: int | None = None
    aux_voltage: float | None = None
    aux_current: float | None = None
    input_raw: str | None = None
    alert_raw: str | None = None
    inhibit_raw: str | None = None
    isolate_raw: str | None = None
    sia_address: int | None = None
    tamper_fault: bool | None = None
    tamper_inhibited: bool | None = None
    tamper_isolated: bool | None = None
    last_event: dict[str, Any] | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    updated_at: datetime | None = None


@dataclass
class SpcState:
    """Complete SPC state."""

    panel: PanelState = field(default_factory=PanelState)
    faults: FaultState = field(default_factory=FaultState)
    areas: dict[int, AreaState] = field(default_factory=dict)
    zones: dict[int, ZoneState] = field(default_factory=dict)
    doors: dict[int, DoorState] = field(default_factory=dict)
    mapping_gates: dict[int, MappingGateState] = field(default_factory=dict)
    ats: dict[int, AtsState] = field(default_factory=dict)
    # ENETNODE.ID is not globally unique on observed multi-branch panels.
    # The hardware serial number (SN) is therefore used as the inventory key.
    xbus_devices: dict[str, XBusDeviceState] = field(default_factory=dict)
    # Active system alerts from GET_ALERT_STATUS: [{"event_id": int, "state": int}].
    alerts: list[dict[str, int | None]] = field(default_factory=list)
    # From CMD_STATUS_PANEL: system alerts by key, and the Ethernet attributes.
    system_alerts: dict[str, Any] = field(default_factory=dict)
    # Panel users without secrets (GET_USER_CONFIG), by USER_ID.
    users: dict[int, Any] = field(default_factory=dict)
    # User profiles (GET_USER_PROFILE_CONFIG), by USER_PROFILE_ID.
    user_profiles: dict[int, Any] = field(default_factory=dict)
    # READ_INTRUDER_CFG: all system options and timers.
    intruder_config: dict[str, str] = field(default_factory=dict)
    # Panel calendars by ID (GET_CALENDAR_CONFIG).
    calendars: dict[int, Any] = field(default_factory=dict)
    # Calendar exception days by ID (CALENDAR_EXCEPT in GET_CALENDAR_CONFIG).
    calendar_exceptions: dict[int, Any] = field(default_factory=dict)
    # Wireless sensors heard by the panel, by radio ID: last_seen, signal,
    # battery, status, receiver_id, heard (lines in the latest log).
    wireless_sensors: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Whether the panel answered GET_WIRELESS_LOG with lines (a receiver).
    wireless_receiver: bool = False
    # Unknown cards, newest first, card numbers masked (GET_UNKNOWN_CARDS).
    unknown_cards: list[dict[str, str]] = field(default_factory=list)
    # Language numbers installed on the panel (READ_LANG_CFG).
    installed_languages: list[int] = field(default_factory=list)
    # VERIFY_USER_ON_PANEL answer for the command login.
    command_login: dict[str, Any] = field(default_factory=dict)
    ethernet: dict[str, str] = field(default_factory=dict)
