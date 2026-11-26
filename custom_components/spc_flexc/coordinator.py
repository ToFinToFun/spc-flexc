"""Data update coordinator for the SPC FlexC integration."""

import asyncio
import logging
import time
import xml.etree.ElementTree as ET
from contextlib import suppress
from datetime import UTC, datetime, timedelta, tzinfo
from functools import partial
from typing import Any
from xml.sax.saxutils import quoteattr

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .activity import SOURCE_LOG, SpcActivityLog, command_names, reply_result
from .const import (
    AREA_DISCOVERY_MAX_ID,
    ATS_IDS,
    CLOCK_SYNC_INTERVAL,
    CLOCK_SYNC_LIMIT,
    CONF_CLOCK_SYNC,
    CONF_ENGINEER_PASSWORD,
    CONF_ENGINEER_USERNAME,
    CONF_USER_ALIASES,
    DEFAULT_PANEL_INTERVAL,
    DOMAIN,
    DOOR_DISCOVERY_MAX_ID,
    ENGINEER_IDLE_LOGOUT,
    XBUS_POLL_INTERVAL,
    XBUS_POLL_PHASE,
    XBUS_TAMPER_INHIBIT_MASK,
    XBUS_TAMPER_INPUT_MASK,
    XBUS_TAMPER_ISOLATE_MASK,
    ZONE_DISCOVERY_MAX_ID,
    ZONE_POLL_BATCH_SIZE,
    ZONE_POLL_INTERVAL,
    ZONE_POLL_PHASE,
)
from .flexc.calendars import DAYS as CALENDAR_DAYS
from .flexc.calendars import (
    CalendarPeriod,
    build_add_calendar_command,
    build_calendar_config_command,
    build_calendar_exception_command,
    build_delete_calendar_command,
    build_delete_calendar_exception_command,
    build_edit_calendar_command,
    build_edit_calendar_week_command,
    parse_calendar_config,
    parse_calendar_exceptions,
)
from .flexc.connection import FlexCClient, FlexCError
from .flexc.discovery import (
    async_discover_areas,
    async_discover_doors,
    async_discover_zones,
)
from .flexc.events import (
    PANEL_ALERT_EVENT_IDS,
    apply_area_event,
    apply_area_intrusion_event,
    apply_event,
    apply_panel_event,
    apply_xbus_event,
    apply_zone_event,
)
from .flexc.flexml import FlexMLError
from .flexc.intruder_config import (
    build_intruder_config_command,
    parse_intruder_config,
)
from .flexc.logs import build_log_command, parse_log
from .flexc.panel_control import (
    ALERT_ACTION_INHIBIT,
    ALERT_ACTION_ISOLATE,
    build_alert_control_command,
    build_clear_all_alerts_command,
    build_engineer_mode_command,
    build_flexc_manual_test_command,
    build_save_config_command,
    build_set_clock_command,
    build_silence_all_bells_command,
    build_verify_user_command,
    parse_simple_reply,
    parse_verify_user,
)
from .flexc.panel_status import (
    SYSTEM_ALERTS,
    build_status_panel_command,
    is_status_panel_unsupported,
    parse_status_panel,
)
from .flexc.profiles import (
    apply_profile_changes,
    build_add_user_profile_command,
    build_delete_user_profile_command,
    build_edit_user_profile_command,
    build_user_profile_config_command,
    parse_user_profile_records,
    user_profile,
)
from .flexc.read_retry import async_retry_read_once
from .flexc.users import (
    apply_user_changes,
    build_add_user_command,
    build_delete_user_command,
    build_edit_user_command,
    build_language_config_command,
    build_unknown_cards_command,
    build_user_status_command,
    encode_pin,
    parse_installed_languages,
    parse_unknown_cards,
    parse_user_records,
    parse_user_status,
    pin_key,
    public_user,
    unknown_card_number,
)
from .flexc.users import build_user_config_command as build_users_command
from .flexc.xbus import async_get_xbus_status
from .flexc.zone_config import (
    apply_zone_changes,
    build_edit_zone_command,
    build_get_zone_config_command,
    parse_edit_zone_reply,
    parse_zone_config,
)
from .models import (
    AreaState,
    AtpState,
    AtsState,
    DoorState,
    PanelState,
    SpcState,
    XBusDeviceState,
    ZoneState,
)
from .pir_diagnostics import PirSlowReadHistory, slow_read_log_level
from .user_names import display_user_name

_LOGGER = logging.getLogger(__name__)


def poll_delay_for_phase(phase: float, interval: float) -> float:
    """Return the delay to the next fixed phase on the monotonic loop clock."""
    now = asyncio.get_running_loop().time()
    position = now % interval
    delay = (phase - position) % interval
    if delay < 0.001:
        return interval
    return delay


def _pir_slow_poll_log_level(elapsed_seconds: float) -> int:
    """Suppress startup-only slow-poll warnings without hiding diagnostics."""
    return logging.DEBUG if elapsed_seconds < 30.0 else logging.WARNING


def _float_value(value: Any, suffix: str = "") -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if suffix and text.endswith(suffix):
        text = text[: -len(suffix)].strip()
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _int_value(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _bool_value(value: Any) -> bool | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "0":
        return False
    if text == "1":
        return True
    return None


def _spc_datetime(value: Any, timezone: tzinfo) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.strptime(str(value).strip(), "%H%M%S%d%m%Y").replace(
            tzinfo=timezone
        )
    except ValueError:
        return None


def _panel_state_from_summary(
    summary: dict[str, str], timezone: tzinfo | None = None
) -> PanelState:
    now = datetime.now(UTC)
    panel_time = _spc_datetime(summary.get("SPC_TIME"), timezone) if timezone else None
    return PanelState(
        battery_voltage=_float_value(summary.get("SPC_BATT_VOLT"), "V"),
        aux_voltage=_float_value(summary.get("SPC_AUX_VOLT"), "V"),
        aux_current=_float_value(summary.get("SPC_AUX_CURR"), "mA"),
        ac_frequency=_float_value(summary.get("SPC_AC_FREQ"), "Hz"),
        rf_type=_int_value(summary.get("SPC_RF_TYPE")),
        rf_version=summary.get("SPC_RF_VERSION"),
        internal_bells=_bool_value(summary.get("INTERNAL_BELLS")),
        external_bells=_bool_value(summary.get("EXTERNAL_BELLS")),
        engineer_mode=_bool_value(summary.get("ENG_MODE")),
        installation_name=summary.get("INSTALLATION_NAME"),
        spc_type=summary.get("SPC_TYPE"),
        spc_variant=summary.get("SPC_VARIANT"),
        serial_number=summary.get("SPC_SERIAL_NO"),
        firmware_version=summary.get("SPC_FW_VERSION"),
        hardware_version=summary.get("SPC_HW_VERSION"),
        panel_time=panel_time,
        clock_offset=None
        if panel_time is None
        else round((panel_time - now).total_seconds()),
        configuration_changed=_spc_datetime(summary.get("TIME_SYSCFG"), timezone)
        if timezone
        else None,
        users_changed=_spc_datetime(summary.get("TIME_USERS"), timezone)
        if timezone
        else None,
        raw=dict(summary),
        updated_at=now,
    )


def _ats_state_from_status(response: dict[str, Any], timezone: tzinfo) -> AtsState:
    raw_ats = response["ats"]
    ats = AtsState(
        ats_id=int(raw_ats["ATS_ID"]),
        name=raw_ats.get("ATS_NAME"),
        registration_id=raw_ats.get("REGISTRATION_ID"),
        status=_int_value(raw_ats.get("ATS_STATUS")),
        state=_int_value(raw_ats.get("ATS_STATE")),
        event_log_count=_int_value(raw_ats.get("EVENT_LOG_COUNT")),
        updated_at=datetime.now(UTC),
    )
    for raw_atp in response["atps"]:
        atp_id = int(raw_atp["ATP_ID"])
        ats.atps[atp_id] = AtpState(
            atp_id=atp_id,
            name=raw_atp.get("ATP_NAME"),
            seq_id=_int_value(raw_atp.get("ATP_SEQ_ID")),
            uid=_int_value(raw_atp.get("ATP_UID")),
            status=_int_value(raw_atp.get("ATP_STATUS")),
            state=_int_value(raw_atp.get("ATP_STATE")),
            connect_state=_int_value(raw_atp.get("ATP_CONNECT_STATE")),
            last_tx_ok_timestamp=_spc_datetime(
                raw_atp.get("LAST_TX_OK_TIMESTAMP"), timezone
            ),
        )
    return ats


def _area_reconciliation_changes(
    previous: dict[str, str], current: dict[str, str]
) -> list[str]:
    """List changed area status keys without exposing values or user names."""
    return [
        key
        for key in sorted(previous.keys() | current.keys())
        if previous.get(key) != current.get(key)
    ]


def _area_state_from_status(raw_area: dict[str, str], timezone: tzinfo) -> AreaState:
    return AreaState(
        area_id=int(raw_area["AREA_ID"]),
        name=raw_area.get("AREA_NAME"),
        mode=_int_value(raw_area.get("MODE")),
        partset_a_enabled=_bool_value(raw_area.get("PARTSETA_ENABLE")),
        partset_b_enabled=_bool_value(raw_area.get("PARTSETB_ENABLE")),
        last_set_time=_spc_datetime(raw_area.get("LAST_SET_TIME"), timezone),
        last_set_user_id=_int_value(raw_area.get("LAST_SET_USER_ID")),
        last_set_user_name=raw_area.get("LAST_SET_USER_NAME"),
        last_unset_time=_spc_datetime(raw_area.get("LAST_UNSET_TIME"), timezone),
        last_unset_user_id=_int_value(raw_area.get("LAST_UNSET_USER_ID")),
        last_unset_user_name=raw_area.get("LAST_UNSET_USER_NAME"),
        last_alarm=_spc_datetime(raw_area.get("LAST_ALARM"), timezone),
        internal_bells=_bool_value(raw_area.get("INTERNAL_BELLS")),
        external_bells=_bool_value(raw_area.get("EXTERNAL_BELLS")),
        raw=dict(raw_area),
        updated_at=datetime.now(UTC),
    )


def _zone_state_from_status(raw_zone: dict[str, str]) -> ZoneState:
    return ZoneState(
        zone_id=int(raw_zone["ZONE_ID"]),
        name=raw_zone.get("ZONE_NAME"),
        area_id=_int_value(raw_zone.get("AREA_ID")),
        area_name=raw_zone.get("AREA_NAME"),
        zone_type=_int_value(raw_zone.get("TYPE")),
        input_state=_int_value(raw_zone.get("INPUT")),
        logic_input=_int_value(raw_zone.get("LOGIC_INPUT")),
        status=_int_value(raw_zone.get("STATUS")),
        proc_state=_int_value(raw_zone.get("PROC_STATE")),
        alarm_state=_int_value(raw_zone.get("ALARM_STATE")),
        inhibit_allowed=_bool_value(raw_zone.get("INHIBIT_ALLOWED")),
        isolate_allowed=_bool_value(raw_zone.get("ISOLATE_ALLOWED")),
        restore_allowed=_bool_value(raw_zone.get("RESTORE_ALLOWED")),
        actuations_since_last_read=_int_value(
            raw_zone.get("ACTUATIONS_SINCE_LAST_READ")
        ),
        raw=dict(raw_zone),
        updated_at=datetime.now(UTC),
    )


def _reconcile_zone_event_state(zone: ZoneState, previous: ZoneState | None) -> bool:
    """Preserve event history, but clear stale tamper on confirmed normal status.

    Only a complete, explicitly normal status can override a missed restore
    EVENT. Missing fields are not evidence of recovery.
    """
    if previous is None:
        return False

    zone.last_event = previous.last_event
    zone.event_tamper = previous.event_tamper
    zone.event_trouble = previous.event_trouble
    # Alarm-zone tamper remains latched until an explicit 1300 restore.
    # A normal PIR snapshot does not prove the panel alarm was restored.
    last_event_id = (previous.last_event or {}).get("EV_ID")
    if (
        str(last_event_id) not in ("1200", "1800")
        and zone.event_tamper is True
        and all(
            value == 0
            for value in (
                zone.logic_input,
                zone.status,
                zone.proc_state,
                zone.alarm_state,
            )
        )
        and all(
            value is not None
            for value in (
                zone.logic_input,
                zone.status,
                zone.proc_state,
                zone.alarm_state,
            )
        )
    ):
        zone.event_tamper = False

    return zone.event_tamper != previous.event_tamper


def _iso(value: Any) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None


def door_state_from_status(
    raw_door: dict[str, str],
    previous: DoorState | None = None,
    areas: dict[int, AreaState] | None = None,
) -> DoorState:
    """Build a door state from DOOR_STATUS, keeping all raw FlexC values.

    State that DOOR_STATUS does not carry (the configured granted time and the
    last Entry Granted event) is carried over from ``previous``.
    """
    door = DoorState(
        door_id=int(raw_door["DOOR_ID"]),
        name=raw_door.get("DOOR_NAME")
        or raw_door.get("NAME")
        or raw_door.get("ZONE_NAME"),
        status=_int_value(raw_door.get("STATUS")),
        mode=_int_value(raw_door.get("DOOR_MODE") or raw_door.get("MODE")),
        dps_input=_int_value(raw_door.get("DPS_INPUT")),
        drs_input=_int_value(raw_door.get("DRS_INPUT")),
        reader1_format=_int_value(raw_door.get("READER1_FORMAT")),
        reader2_format=_int_value(raw_door.get("READER2_FORMAT")),
        zone_id=_int_value(raw_door.get("ZONE_ID")),
        zone_name=raw_door.get("ZONE_NAME"),
        area_id=_int_value(raw_door.get("AREA_ID")),
        area_name=raw_door.get("AREA_NAME"),
        area_side_1=_int_value(raw_door.get("AREA_SIDE_1")),
        area_side_1_name=raw_door.get("AREA_SIDE_1_NAME"),
        area_side_2=_int_value(raw_door.get("AREA_SIDE_2")),
        area_side_2_name=raw_door.get("AREA_SIDE_2_NAME"),
        entry_exit=_bool_value(raw_door.get("ENTRY_EXIT")),
        normal_allowed=_bool_value(raw_door.get("NORMAL_ALLOWED")),
        lock_allowed=_bool_value(raw_door.get("LOCK_ALLOWED")),
        unlock_allowed=_bool_value(raw_door.get("UNLOCK_ALLOWED")),
        momentary_allowed=_bool_value(raw_door.get("MOMENTARY_ALLOWED")),
        raw=dict(raw_door),
        updated_at=datetime.now(UTC),
        granted_time=None if previous is None else previous.granted_time,
        config_side_entry=None if previous is None else previous.config_side_entry,
        config_side_exit=None if previous is None else previous.config_side_exit,
        dps_normally_open=None if previous is None else previous.dps_normally_open,
        drs_normally_open=None if previous is None else previous.drs_normally_open,
        drs_ignored=None if previous is None else previous.drs_ignored,
        entry_granted_at=None if previous is None else previous.entry_granted_at,
        entry_granted_until=None if previous is None else previous.entry_granted_until,
    )
    if areas is not None:
        apply_config_sides(door, areas)
    return door


def apply_config_sides(door: DoorState, areas: dict[int, AreaState]) -> None:
    """Use the door sides from GET_DOOR_CONFIG once they are read.

    DOOR_STATUS reports the entry and exit side areas one higher than the
    web page and DOOR_CONFIG (checked 2026-11-13 on door 2: area 1 set on
    the web page reads AREA_SIDE_1="2" Garaget), so the configured
    DOOR_SIDE_0 / DOOR_SIDE_1 win, with the area's own name.
    """
    for side, attr in (
        (door.config_side_entry, "area_side_1"),
        (door.config_side_exit, "area_side_2"),
    ):
        if side is None:
            continue
        area = areas.get(side) if side else None
        setattr(door, attr, side or None)
        setattr(door, f"{attr}_name", area.name if area is not None else None)


def _xbus_mask_state(raw_value: str | None, mask: int) -> bool | None:
    """Return a validated X-BUS bit state from a hexadecimal status field."""
    if raw_value is None:
        return None
    try:
        return bool(int(raw_value, 16) & mask)
    except ValueError:
        return None


def _xbus_device_state_from_status(
    raw_device: dict[str, str],
    previous: XBusDeviceState | None = None,
) -> XBusDeviceState | None:
    """Build an X-BUS device and reconcile tamper state from status."""
    device_id = _int_value(raw_device.get("ID"))
    if device_id is None:
        _LOGGER.warning("Ignoring X-BUS ENETNODE without a valid ID: %s", raw_device)
        return None

    return XBusDeviceState(
        device_id=device_id,
        name=raw_device.get("NAME"),
        serial_number=raw_device.get("SN"),
        device_type=_int_value(raw_device.get("TYPE")),
        hardware_id=_int_value(raw_device.get("HARDWARE_ID")),
        input_count=_int_value(raw_device.get("ICOUNT")),
        output_count=_int_value(raw_device.get("OCOUNT")),
        version=raw_device.get("VERSION"),
        rf_type=_int_value(raw_device.get("RF_TYPE")),
        rf_version=raw_device.get("RF_VERSION"),
        reader_type=_int_value(raw_device.get("READER_TYPE")),
        status_raw=raw_device.get("STATUS"),
        position_1=_int_value(raw_device.get("POSITION_1")),
        position_2=_int_value(raw_device.get("POSITION_2")),
        psu_type=_int_value(raw_device.get("PSU_TYPE")),
        aux_voltage=_float_value(raw_device.get("AUX_VOLT"), "V"),
        aux_current=_float_value(raw_device.get("AUX_CURR"), "mA"),
        input_raw=raw_device.get("INPUT"),
        alert_raw=raw_device.get("ALERT"),
        inhibit_raw=raw_device.get("INHIBIT"),
        isolate_raw=raw_device.get("ISOLATE"),
        sia_address=previous.sia_address if previous is not None else None,
        tamper_fault=_xbus_mask_state(raw_device.get("INPUT"), XBUS_TAMPER_INPUT_MASK),
        tamper_inhibited=_xbus_mask_state(
            raw_device.get("INHIBIT"), XBUS_TAMPER_INHIBIT_MASK
        ),
        tamper_isolated=_xbus_mask_state(
            raw_device.get("ISOLATE"), XBUS_TAMPER_ISOLATE_MASK
        ),
        last_event=previous.last_event if previous is not None else None,
        raw=dict(raw_device),
        updated_at=datetime.now(UTC),
    )


class SpcFlexCCoordinator(DataUpdateCoordinator[SpcState]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_PANEL_INTERVAL),
        )
        self.entry = entry
        self.state = SpcState()
        self._tamper_store: Store[dict[str, bool]] = Store(
            hass, 1, f"{DOMAIN}.panel_tamper.{entry.entry_id}"
        )
        self._area_history_store: Store[dict[str, Any]] = Store(
            hass, 1, f"{DOMAIN}.area_history.{entry.entry_id}"
        )
        self._area_history: dict[int, dict[str, Any]] = {}
        # Per door: the last unlock (entry granted, exit granted or exit
        # button, with who) and the last time the door was opened (DPS).
        # Kept across restarts; unlocks are also read back from the access log.
        self._door_history_store: Store[dict[str, Any]] = Store(
            hass, 1, f"{DOMAIN}.door_history.{entry.entry_id}"
        )
        self._door_history: dict[int, dict[str, Any]] = {}
        # Door commands sent from Home Assistant, by door: (monotonic time,
        # the Home Assistant user's name), to name the unlock the panel then
        # reports with the integration's own login (user "Kommandoprofilan").
        self._ha_door_requests: dict[int, tuple[float, str | None]] = {}
        # PIN keys of the users whose PIN the owner let Home Assistant manage
        # (enable_pin_management), by user number. Never logged or shown.
        self._pin_key_store: Store[dict[str, dict[str, Any]]] = Store(
            hass, 1, f"{DOMAIN}.pin_keys.{entry.entry_id}"
        )
        self._pin_keys: dict[int, dict[str, Any]] = {}
        self._user_names: dict[int, str] = {}
        self.client = FlexCClient(entry.data)
        self.client.set_event_callback(self._handle_flexc_event)
        self.client.set_session_ready_callback(self._handle_session_ready)
        # What HA sends, what the panel answers, its events and log lines.
        self.activity = SpcActivityLog(hass, entry.entry_id)
        self.client.set_command_observer(self._observe_command)
        self._activity_seen: set[tuple[Any, ...]] | None = None
        self._activity_handle: asyncio.TimerHandle | None = None
        self._activity_task: asyncio.Task[None] | None = None
        self._activity_last_read = 0.0
        # Last answer of every command name, for the Capabilities sensor.
        self.command_results: dict[str, dict[str, Any]] = {}
        self._login_checked = False
        # Options at setup; a later data-only update (engineer login) must
        # not reload the integration.
        self.loaded_options: dict[str, Any] = dict(entry.options)
        self._last_own_config_change: float | None = None
        # Programtekniker (engineer) login: kept in memory for this session,
        # or remembered in the config entry when the owner chose to.
        self._engineer: dict[str, Any] | None = None
        if entry.data.get(CONF_ENGINEER_USERNAME) and entry.data.get(
            CONF_ENGINEER_PASSWORD
        ):
            self._engineer = {
                "username": entry.data[CONF_ENGINEER_USERNAME],
                "password": entry.data[CONF_ENGINEER_PASSWORD],
                "remember": True,
                "user_id": None,
                "last_used": time.monotonic(),
            }
        else:
            # A login that is not remembered survives a reload (for example
            # after a zone rename) but not a restart: it is kept in hass.data.
            self._engineer = self._engineer_sessions().get(entry.entry_id)
        self._detected_ats_ids: set[int] = set()
        self._ats_discovery_complete = False
        self._detected_area_ids: set[int] = set()
        self._area_discovery_complete = False
        self._detected_zone_ids: set[int] = set()
        self._zone_discovery_complete = False
        self._pending_zone_restores: set[tuple[int, int]] = set()
        # Monotonic generation for PIR EVENT transitions; used to reject
        # in-flight polling snapshots older than a received live EVENT.
        self._pir_event_generation: dict[int, int] = {}
        self.pir_slow_reads = PirSlowReadHistory()
        self._detected_door_ids: set[int] = set()
        self._door_discovery_complete = False
        self._detected_xbus_serials: set[str] = set()
        self._xbus_discovery_complete = False
        self._discovery_requested = False
        self._client_operation_lock = asyncio.Lock()
        self._discovery_task: asyncio.Task[None] | None = None
        self._zone_poll_task: asyncio.Task[None] | None = None
        self._xbus_poll_task: asyncio.Task[None] | None = None
        self._reconnect_reconcile_task: asyncio.Task[None] | None = None
        self._pending_reconcile_generation = 0
        self._last_reconciled_generation = 0

    # Commands that change the panel configuration themselves; a change of
    # TIME_SYSCFG right after one of them is ours and needs no reload.
    _OWN_CONFIG_COMMANDS = ("SAVE_CONFIG",)
    OWN_CHANGE_GRACE = 600.0

    def async_set_updated_data(self, data: SpcState) -> None:
        """Push new state to the entities without moving the periodic refresh.

        Home Assistant's version also restarts the update_interval timer.
        The integration pushes state from events and fast polls far more
        often than every DEFAULT_PANEL_INTERVAL, so with it the periodic
        refresh (panel summary, alerts, TIME_SYSCFG and so name changes
        on the panel) never ran after start-up (found 2026-11-13: no
        periodic fetch in 4 minutes, pushes every 30 s).
        """
        self.data = data
        self.last_update_success = True
        self.async_update_listeners()

    def _check_configuration_change(self, previous: Any) -> None:
        """Reload the integration when the panel configuration changed.

        The panel moves TIME_SYSCFG on every configuration change (names,
        zones, doors, areas, X-BUS). A reload reads everything again, so
        Home Assistant follows the panel. Changes made by this integration
        (followed by SAVE_CONFIG) do not reload it: the first change seen
        within OWN_CHANGE_GRACE of our own SAVE_CONFIG is taken as ours and
        used up, so a later change made on the panel's web page still
        reloads (found 2026-11-13: a rename on the web page a few minutes
        after a profile edit from Home Assistant was never picked up).
        """
        current = self.state.panel.configuration_changed
        if previous is None or current is None or current == previous:
            return
        if not self._discovery_complete:
            return
        last_own = self._last_own_config_change
        if (
            last_own is not None
            and self.hass.loop.time() - last_own < self.OWN_CHANGE_GRACE
        ):
            self._last_own_config_change = None
            return
        _LOGGER.info(
            "SPC configuration changed on the panel (%s); reloading to follow it",
            current,
        )
        self.activity.add(
            SOURCE_LOG,
            "SPC",
            "Panel configuration changed: reading names, zones, doors and X-BUS again",
        )
        self.hass.config_entries.async_schedule_reload(self.entry.entry_id)

    def _observe_command(self, command: str) -> Any:
        """Record every command's answer; log state-changing ones as activity."""
        all_names = command_names(command)
        logged = self.activity.add_command(command)

        def done(reply: str | None, error: str | None) -> None:
            _, result, _ = reply_result(reply or "")
            if result == 0 and any(
                name in self._OWN_CONFIG_COMMANDS for name in all_names
            ):
                self._last_own_config_change = self.hass.loop.time()
            now = dt_util.now().isoformat()
            for name in all_names:
                self.command_results[name] = {
                    "result": result,
                    "error": error,
                    "time": now,
                }
            if logged:
                self.activity.add_reply(logged, reply, error)
                self.schedule_activity_log_read()

        return done

    async def _async_read_wireless_locked(self) -> None:
        """Read the wireless log and keep the latest line of every sensor."""
        if getattr(self, "_wireless_unsupported", False):
            return
        command = build_log_command(
            "wireless", None, self.client.command_username, self.client.command_password
        )
        try:
            response = await async_retry_read_once(
                partial(self.client.async_send_flexml, command),
                description="reading the wireless log",
            )
            records = parse_log(response, "wireless", dt_util.get_default_time_zone())
        except FlexMLError as err:
            _LOGGER.debug("No wireless log: %s", err)
            self._wireless_unsupported = True
            return
        sensors = dict(self.state.wireless_sensors)
        heard: dict[str, int] = {}
        for record in reversed(records):  # oldest first, newest wins
            radio_id = str(record.get("radio_id") or "")
            if not radio_id:
                continue
            heard[radio_id] = heard.get(radio_id, 0) + 1
            sensors[radio_id] = {
                "last_seen": record.get("time"),
                "signal": record.get("signal"),
                "battery": record.get("battery"),
                "status": record.get("status"),
                "receiver_id": record.get("receiver_id"),
            }
        for radio_id, entry in sensors.items():
            entry["heard"] = heard.get(radio_id, 0)
        self.state.wireless_sensors = sensors
        self.state.wireless_receiver = self.state.wireless_receiver or bool(records)

    async def _async_check_login_locked(self) -> None:
        """Ask the panel about the command login once (VERIFY_USER_ON_PANEL).

        The answer says whether the login is an engineer and has remote
        access; it ignores any user or PIN attributes.
        """
        if self._login_checked:
            return
        self._login_checked = True
        command = (
            '<FLEXML_CMD VER="1.0" '
            f"PANEL_USERNAME={quoteattr(self.client.command_username)} "
            f"PANEL_PASSWORD={quoteattr(self.client.command_password)}>"
            "<CMD_VERIFY_USER_ON_PANEL /></FLEXML_CMD>"
        )
        try:
            response = await self.client.async_send_flexml(command)
            element = ET.fromstring(response).find(".//VERIFY_USER")
        except (FlexCError, ET.ParseError) as err:
            _LOGGER.debug("VERIFY_USER_ON_PANEL failed: %s", err)
            return
        if element is not None:
            self.state.command_login = {
                "user_id": _int_value(element.get("USER_ID")),
                "engineer": element.get("ENGINEER") == "1",
                "remote_access": element.get("REMOTE_ACCESS") == "1",
            }

    def schedule_activity_log_read(self, delay: float = 5.0) -> None:
        """Read the panel's system and access logs soon (debounced).

        Called after a command and after a panel event. Reads at most every
        30 seconds; the first read only remembers what is already in the logs.
        """
        if self._activity_task is not None and not self._activity_task.done():
            return
        loop = self.hass.loop
        wait = max(delay, 30.0 - (loop.time() - self._activity_last_read))
        if self._activity_handle is not None:
            self._activity_handle.cancel()

        def start() -> None:
            self._activity_handle = None
            self._activity_task = self.entry.async_create_background_task(
                self.hass,
                self._async_read_activity_logs(),
                name=f"{DOMAIN} activity log read",
                eager_start=False,
            )

        self._activity_handle = loop.call_later(wait, start)

    async def _async_read_activity_logs(self) -> None:
        """Add new lines of the system and access logs to the activity log."""
        self._activity_last_read = self.hass.loop.time()
        lines: list[tuple[str, dict[str, Any]]] = []
        try:
            lines += [("system", r) for r in await self.async_read_log("system")]
            for door_id in sorted(self.state.doors):
                lines += [
                    ("access", r) for r in await self.async_read_log("access", door_id)
                ]
        except (FlexCError, FlexMLError) as err:
            _LOGGER.debug("Could not read the panel logs for the activity log: %s", err)
            return

        def key(kind: str, record: dict[str, Any]) -> tuple[Any, ...]:
            return (
                kind,
                record.get("time"),
                record.get("door_id"),
                record.get("type"),
                record.get("raw"),
                record.get("text"),
            )

        self._note_unlocks_from_access_log([r for kind, r in lines if kind == "access"])
        keys = {key(kind, record) for kind, record in lines}
        if self._activity_seen is None:
            self._activity_seen = keys
            return
        new = [
            (kind, r) for kind, r in lines if key(kind, r) not in self._activity_seen
        ]
        self._activity_seen = keys
        new.sort(key=lambda item: item[1].get("time") or "")
        for kind, record in new:
            if kind == "access":
                title = str(record.get("door_name") or f"Door {record.get('door_id')}")
                ok = None
                if record.get("type_name") == "granted":
                    ok = True
                elif record.get("type_name") in (
                    "denied",
                    "forced_open",
                    "unknown_card",
                    "code_lockout",
                ):
                    ok = False
            else:
                title = "Panel log"
                ok = None
            self.activity.add(
                SOURCE_LOG,
                title,
                str(record.get("text") or ""),
                ok=ok,
                panel_time=record.get("time"),
                log=kind,
                door_id=record.get("door_id"),
                user_id=record.get("user_id"),
                user_name=self.unlocker_name(
                    record.get("user_id"),
                    record.get("user_name"),
                    record.get("door_id"),
                ),
            )

    def _note_unlocks_from_access_log(self, records: list[dict[str, Any]]) -> None:
        """Take each door's last unlock from its access log, oldest first.

        Granted (1) and "Dörr olåst" (11) count, with the user. The exit button
        (5) counts only when the door was not already unlocked: an exit button
        in the door handle is pressed by everyone who opens the door after a
        card or code, or while the door stands unlocked (owner 2026-11-14).
        """
        state: dict[int, dict[str, Any]] = {}

        # The log has whole seconds and lists rows newest first, so a code and
        # the handle's exit button can share a second in either order; within
        # a second, everything else goes before the exit button.
        def order(record: dict[str, Any]) -> tuple[str, int]:
            return (
                str(record.get("time") or ""),
                record.get("type_name") == "door_release",
            )

        for record in sorted(records, key=order):
            door_id = record.get("door_id")
            when = dt_util.parse_datetime(str(record.get("time") or ""))
            if not isinstance(door_id, int) or when is None:
                continue
            if when.tzinfo is None:
                when = when.replace(tzinfo=dt_util.get_default_time_zone())
            door_state = state.setdefault(door_id, {"until": None, "unlocked": False})
            kind = record.get("type_name")
            user_id = record.get("user_id")
            user_id = user_id if isinstance(user_id, int) else None
            name = self.unlocker_name(user_id, record.get("user_name"))
            if kind == "granted":
                door = self.state.doors.get(door_id)
                seconds = (door.granted_time if door else None) or 3
                door_state["until"] = when + timedelta(seconds=seconds + 2)
                self.note_door_unlocked(door_id, when, "granted", user_id, name)
            elif kind == "door_unlocked":
                door_state["unlocked"] = True
                self.note_door_unlocked(door_id, when, "unlocked", user_id, name)
            elif kind in ("door_normal", "door_blocked"):
                door_state["unlocked"] = False
            elif kind == "door_release":
                until = door_state["until"]
                if door_state["unlocked"] or (until is not None and when <= until):
                    continue
                self.note_door_unlocked(door_id, when, "exit_button")

    async def _async_read_calendars_locked(self, force: bool = False) -> None:
        """Read the panel calendars when the panel configuration changed.

        Called with the client operation lock held. Best effort: a panel or
        command profile without GET_CALENDAR_CONFIG only loses calendars.
        """
        if getattr(self, "_calendars_unsupported", False):
            return
        stamp = self.state.panel.configuration_changed
        if (
            not force
            and self.state.calendars
            and stamp is not None
            and stamp == getattr(self, "_calendars_read_for", None)
        ):
            return
        command = build_calendar_config_command(
            self.client.command_username, self.client.command_password
        )
        try:
            response = await async_retry_read_once(
                partial(self.client.async_send_flexml, command),
                description="reading calendars",
            )
            self.state.calendars = parse_calendar_config(response)
            self.state.calendar_exceptions = parse_calendar_exceptions(response)
        except FlexMLError as err:
            _LOGGER.info("GET_CALENDAR_CONFIG not available, skipping it: %s", err)
            self._calendars_unsupported = True
            return
        self._calendars_read_for = stamp

    async def _async_read_users_locked(self, force: bool = False) -> None:
        """Read all users when the panel's user list changed (best effort).

        Only fields without secrets are kept (see flexc/users.py).
        """
        if getattr(self, "_users_unsupported", False):
            return
        stamp = self.state.panel.users_changed
        if (
            not force
            and self.state.users
            and stamp is not None
            and stamp == getattr(self, "_users_read_for", None)
        ):
            return
        command = build_users_command(
            0, self.client.command_username, self.client.command_password
        )
        try:
            response = await async_retry_read_once(
                partial(self.client.async_send_flexml, command),
                description="reading users",
            )
            records = parse_user_records(response)
        except FlexMLError as err:
            _LOGGER.info("GET_USER_CONFIG not available, skipping users: %s", err)
            self._users_unsupported = True
            return
        users = {}
        for record in records:
            try:
                user = public_user(record)
            except (KeyError, ValueError):
                continue
            users[user.user_id] = user
        self.state.users = users
        self._users_read_for = stamp

    async def _async_read_user_record_locked(self, user_id: int) -> dict[str, str]:
        """Read one user's whole record, secrets included (lock held, not stored)."""
        command = build_users_command(
            user_id, self.client.command_username, self.client.command_password
        )
        response = await async_retry_read_once(
            partial(self.client.async_send_flexml, command),
            description=f"reading user {user_id}",
        )
        records = [
            r for r in parse_user_records(response) if r.get("USER_ID") == str(user_id)
        ]
        if not records:
            raise ValueError(f"The panel has no user {user_id}")
        return records[0]

    async def async_edit_user(
        self,
        user_id: int,
        *,
        name: str | None = None,
        profiles: list[int] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        card_number: str | None = None,
        card_options: dict[str, bool] | None = None,
        language: int | None = None,
    ) -> None:
        """Change a user's name, profiles, dates, card or language.

        Read-modify-write: the record is read just before the edit.

        The record is read just before the edit and sent back whole without
        WEBPASS_DATA; secrets are not kept after the call.
        """
        async with self._client_operation_lock:
            await self.client.async_ensure_connected()
            record = await self._async_read_user_record_locked(user_id)
            updated = apply_user_changes(
                record,
                name=name,
                profiles=profiles,
                start_date=start_date,
                end_date=end_date,
                card_number=card_number,
                card_options=card_options,
                language=language,
            )
            command = build_edit_user_command(
                updated, self.client.command_username, self.client.command_password
            )
            del record, updated
            response = await self.client.async_send_flexml(command)
            del command
            parse_simple_reply(response, "EDIT_USER")
            await self._async_save_config_locked()
            await self._async_read_users_locked(force=True)
        _LOGGER.info("SPC user %d changed", user_id)
        self.async_set_updated_data(self.state)

    async def async_restore_pin_keys(self) -> None:
        """Load the stored PIN keys (best effort)."""
        try:
            saved = await self._pin_key_store.async_load()
        except Exception:
            _LOGGER.exception("Could not load the SPC PIN keys")
            return
        if not isinstance(saved, dict):
            return
        for raw_id, value in saved.items():
            user_id = _int_value(raw_id)
            if user_id is None or not isinstance(value, dict):
                continue
            key = value.get("key")
            if isinstance(key, str) and len(key) == 8:
                self._pin_keys[user_id] = {
                    "key": key,
                    "confirmed": bool(value.get("confirmed")),
                    "pending": bool(value.get("pending")),
                }

    def _save_pin_keys(self) -> dict[str, dict[str, Any]]:
        return {str(user_id): dict(value) for user_id, value in self._pin_keys.items()}

    def _store_pin_keys(self) -> None:
        self._pin_key_store.async_delay_save(self._save_pin_keys, 1)

    def pin_managed_numbers(self) -> dict[int, str]:
        """User numbers whose PIN HA may manage, with their status.

        The consent belongs to the user number, not to the person: it stays
        when the user is deleted, so the next user on that number is managed
        too.
        """
        return {
            user_id: "confirmed" if entry["confirmed"] else "unconfirmed"
            for user_id, entry in sorted(self._pin_keys.items())
        }

    def pin_management(self, user_id: int) -> str | None:
        """Return the state of a user's PIN key, or None (not managed by HA).

        "confirmed": a PIN set from here has been used. "pending": a PIN was
        set from here and waits to be used. "unconfirmed": the key was learnt
        from the PIN the owner gave and is unchecked until a PIN set from here
        has been used (a wrong PIN given would give a wrong key).
        """
        entry = self._pin_keys.get(user_id)
        if entry is None:
            return None
        if entry["confirmed"]:
            return "confirmed"
        return "pending" if entry.get("pending") else "unconfirmed"

    async def async_enable_pin_management(self, user_id: int, pin: str) -> None:
        """Learn and store a user's PIN key from its current PIN (owner's consent).

        The PIN cannot be checked over FlexC, so a wrong PIN gives a wrong
        key. The key stays unconfirmed until a PIN that Home Assistant set has
        been used: a keypad login, or a granted entry or exit at a door by a
        user without a card.
        """
        async with self._client_operation_lock:
            await self.client.async_ensure_connected()
            record = await self._async_read_user_record_locked(user_id)
            key = pin_key(record.get("PIN", ""), pin)
            del record
        self._pin_keys[user_id] = {"key": key, "confirmed": False, "pending": False}
        del key
        self._store_pin_keys()
        _LOGGER.info("SPC user %d: PIN management enabled", user_id)
        self.async_set_updated_data(self.state)

    async def async_disable_pin_management(self, user_id: int) -> None:
        """Forget a user's stored PIN key."""
        if self._pin_keys.pop(user_id, None) is not None:
            self._store_pin_keys()
            _LOGGER.info("SPC user %d: PIN management disabled", user_id)
        self.async_set_updated_data(self.state)

    def _key_for(
        self, user_id: int, record: dict[str, str], current_pin: str | None
    ) -> str:
        if current_pin is not None:
            return pin_key(record.get("PIN", ""), current_pin)
        entry = self._pin_keys.get(user_id)
        if entry is None:
            raise ValueError(
                f"User {user_id}: give the current PIN, or enable PIN management first"
            )
        return str(entry["key"])

    def _mark_pin_set(self, user_id: int) -> None:
        entry = self._pin_keys.get(user_id)
        if entry is not None and not entry["confirmed"]:
            entry["pending"] = True
            self._store_pin_keys()

    def _confirm_pin_from_event(
        self, event_id: int | None, user_id: int | None
    ) -> None:
        """Confirm a PIN key when an event shows the user's PIN was used.

        4003: logged in at a keypad. 3000/3002: entry or exit granted at a
        door, which proves the PIN only for a user without a card. A guest's
        profile often has no areas, and then a keypad login sends no 4003
        (owner 2026-11-14), so the door is the usual way.
        """
        if event_id == 4003:
            self._confirm_pin_key(user_id)
        elif event_id in (3000, 3002) and user_id is not None:
            user = self.state.users.get(user_id)
            if user is not None and not getattr(user, "has_card", True):
                self._confirm_pin_key(user_id)

    def _confirm_pin_key(self, user_id: int | None) -> None:
        """A user logged in at a keypad: confirm its key if HA set its PIN."""
        if user_id is None:
            return
        entry = self._pin_keys.get(user_id)
        if entry is not None and entry["pending"] and not entry["confirmed"]:
            entry["confirmed"] = True
            entry["pending"] = False
            self._store_pin_keys()
            _LOGGER.info("SPC user %d: PIN key confirmed", user_id)

    async def async_set_pin(
        self, user_id: int, new_pin: str, current_pin: str | None = None
    ) -> None:
        """Change a user's PIN (EDIT_USER + SAVE_CONFIG, sent once).

        Uses the current PIN when given, otherwise the stored key (PIN
        management). The PINs, the key and the record only live in memory
        during the call and are never logged. The stored PIN is read back.
        """
        async with self._client_operation_lock:
            await self.client.async_ensure_connected()
            record = await self._async_read_user_record_locked(user_id)
            expected = encode_pin(self._key_for(user_id, record, current_pin), new_pin)
            updated = {**record, "PIN": expected}
            command = build_edit_user_command(
                updated, self.client.command_username, self.client.command_password
            )
            del record, updated
            response = await self.client.async_send_flexml(command)
            del command
            parse_simple_reply(response, "EDIT_USER")
            await self._async_save_config_locked()
            check = await self._async_read_user_record_locked(user_id)
            ok = check.get("PIN", "").upper() == expected
            del check, expected
            await self._async_read_users_locked(force=True)
        if not ok:
            raise FlexMLError(f"PIN of user {user_id} did not read back as set")
        self._mark_pin_set(user_id)
        _LOGGER.info("SPC user %d PIN changed", user_id)
        self.async_set_updated_data(self.state)

    async def async_add_user(
        self,
        user_id: int,
        name: str,
        profiles: list[int],
        pin: str,
        start_date: str = "0",
        end_date: str = "0",
        card_number: str | None = None,
        language: int | None = None,
    ) -> None:
        """Add a user with a PIN (ADD_USER + SAVE_CONFIG, sent once).

        Needs the stored key of this user number (PIN management enabled
        while the user existed); the key stays the same for a user number.
        """
        entry = self._pin_keys.get(user_id)
        if entry is None:
            raise ValueError(
                f"User {user_id}: no PIN key stored; create the user once in the "
                "panel and enable PIN management for it"
            )
        await self._async_send_panel_command(
            build_add_user_command(
                user_id,
                name,
                profiles,
                encode_pin(str(entry["key"]), pin),
                self.client.command_username,
                self.client.command_password,
                start_date,
                end_date,
                card_number,
                language,
            ),
            "ADD_USER",
            save=True,
        )
        self._mark_pin_set(user_id)
        async with self._client_operation_lock:
            await self._async_read_users_locked(force=True)
        self.async_set_updated_data(self.state)

    async def async_delete_user(self, user_id: int) -> None:
        """Delete a user (DELETE_USER, sent once). UNTESTED on a panel."""
        await self._async_send_panel_command(
            build_delete_user_command(
                user_id, self.client.command_username, self.client.command_password
            ),
            "DELETE_USER",
            save=True,
        )
        async with self._client_operation_lock:
            await self._async_read_users_locked(force=True)
        self.async_set_updated_data(self.state)

    async def async_read_user_status(self, user_id: int) -> dict[str, Any]:
        """Read one user's status (GET_USER_STATUS); nothing is stored."""
        command = build_user_status_command(
            user_id, self.client.command_username, self.client.command_password
        )
        async with self._client_operation_lock:
            await self.client.async_ensure_connected()
            response = await async_retry_read_once(
                partial(self.client.async_send_flexml, command),
                description=f"reading status of user {user_id}",
            )
        return parse_user_status(response)

    async def async_assign_unknown_card(self, user_id: int, index: int = 1) -> None:
        """Give a user the card of unknown card ``index`` (1 = newest).

        Like the web page's "Okänt kort": the number is read from
        GET_UNKNOWN_CARDS and written with EDIT_USER; it is never shown.
        """
        command = build_unknown_cards_command(
            self.client.command_username, self.client.command_password
        )
        async with self._client_operation_lock:
            await self.client.async_ensure_connected()
            response = await self.client.async_send_flexml(command)
        card_number = unknown_card_number(response, index)
        del response
        await self.async_edit_user(user_id, card_number=card_number)

    async def _async_read_unknown_cards_locked(self, force: bool = False) -> None:
        """Keep the masked unknown-card list fresh (every 5 minutes, best effort)."""
        if getattr(self, "_unknown_cards_unsupported", False):
            return
        now = time.monotonic()
        if not force and now - getattr(self, "_unknown_cards_read_at", -1e9) < 300:
            return
        self._unknown_cards_read_at = now
        command = build_unknown_cards_command(
            self.client.command_username, self.client.command_password
        )
        try:
            response = await self.client.async_send_flexml(command)
            self.state.unknown_cards = parse_unknown_cards(response)
        except FlexMLError as err:
            _LOGGER.debug("No unknown cards: %s", err)
            self._unknown_cards_unsupported = True
        except Exception as err:  # noqa: BLE001 - best effort, retried later
            _LOGGER.debug("Unknown cards not read: %s", err)

    async def async_read_unknown_cards(self) -> list[dict[str, str]]:
        """Read the unknown cards (GET_UNKNOWN_CARDS), newest first.

        Card numbers are masked by the parser; nothing is stored.
        """
        command = build_unknown_cards_command(
            self.client.command_username, self.client.command_password
        )
        async with self._client_operation_lock:
            await self.client.async_ensure_connected()
            response = await async_retry_read_once(
                partial(self.client.async_send_flexml, command),
                description="reading unknown cards",
            )
        self.state.unknown_cards = parse_unknown_cards(response)
        self.async_set_updated_data(self.state)
        return self.state.unknown_cards

    async def _async_read_user_profiles_locked(self, force: bool = False) -> None:
        """Read all user profiles when users or configuration changed (best effort).

        It is not known which change time the panel moves when a profile
        changes, so both are watched.
        """
        if getattr(self, "_user_profiles_unsupported", False):
            return
        stamp = (self.state.panel.users_changed, self.state.panel.configuration_changed)
        if (
            not force
            and self.state.user_profiles
            and None not in stamp
            and stamp == getattr(self, "_user_profiles_read_for", None)
        ):
            return
        command = build_user_profile_config_command(
            0, self.client.command_username, self.client.command_password
        )
        try:
            response = await async_retry_read_once(
                partial(self.client.async_send_flexml, command),
                description="reading user profiles",
            )
            records = parse_user_profile_records(response)
        except FlexMLError as err:
            _LOGGER.info("GET_USER_PROFILE_CONFIG not available, skipping it: %s", err)
            self._user_profiles_unsupported = True
            return
        profiles = {}
        for record in records:
            try:
                profile = user_profile(record)
            except (KeyError, ValueError):
                continue
            profiles[profile.profile_id] = profile
        self.state.user_profiles = profiles
        self._user_profiles_read_for = stamp

    async def _async_read_user_profile_record_locked(
        self, profile_id: int
    ) -> dict[str, str]:
        """Read one profile's whole record (lock held)."""
        command = build_user_profile_config_command(
            profile_id, self.client.command_username, self.client.command_password
        )
        response = await async_retry_read_once(
            partial(self.client.async_send_flexml, command),
            description=f"reading user profile {profile_id}",
        )
        records = [
            r
            for r in parse_user_profile_records(response)
            if r.get("USER_PROFILE_ID") == str(profile_id)
        ]
        if not records:
            raise ValueError(f"The panel has no user profile {profile_id}")
        return records[0]

    async def async_edit_user_profile(
        self,
        profile_id: int,
        *,
        name: str | None = None,
        areas: list[int] | None = None,
        calendar: int | None = None,
        doors: dict[int, str | None] | None = None,
    ) -> None:
        """Change a profile (read-modify-write, sent once). UNTESTED on a panel."""
        async with self._client_operation_lock:
            await self.client.async_ensure_connected()
            record = await self._async_read_user_profile_record_locked(profile_id)
            updated = apply_profile_changes(
                record, name=name, areas=areas, calendar=calendar, doors=doors
            )
            command = build_edit_user_profile_command(
                updated, self.client.command_username, self.client.command_password
            )
            response = await self.client.async_send_flexml(command)
            parse_simple_reply(response, "EDIT_USER_PROFILE")
            await self._async_save_config_locked()
            await self._async_read_user_profiles_locked(force=True)
        _LOGGER.info("SPC user profile %d changed", profile_id)
        self.async_set_updated_data(self.state)

    async def async_add_user_profile(
        self, profile_id: int, name: str, areas: list[int], calendar: int
    ) -> None:
        """Add a profile (ADD_USER_PROFILE, sent once). UNTESTED on a panel."""
        await self._async_send_panel_command(
            build_add_user_profile_command(
                profile_id,
                name,
                areas,
                calendar,
                self.client.command_username,
                self.client.command_password,
            ),
            "ADD_USER_PROFILE",
            save=True,
        )
        async with self._client_operation_lock:
            await self._async_read_user_profiles_locked(force=True)
        self.async_set_updated_data(self.state)

    async def async_delete_user_profile(self, profile_id: int) -> None:
        """Delete a profile (DELETE_USER_PROFILE, sent once). UNTESTED on a panel."""
        await self._async_send_panel_command(
            build_delete_user_profile_command(
                profile_id, self.client.command_username, self.client.command_password
            ),
            "DELETE_USER_PROFILE",
            save=True,
        )
        async with self._client_operation_lock:
            await self._async_read_user_profiles_locked(force=True)
        self.async_set_updated_data(self.state)

    async def _async_read_intruder_config_locked(self) -> None:
        """Read READ_INTRUDER_CFG when the configuration changed (best effort)."""
        if getattr(self, "_intruder_config_unsupported", False):
            return
        stamp = self.state.panel.configuration_changed
        if (
            self.state.intruder_config
            and stamp is not None
            and stamp == getattr(self, "_intruder_config_read_for", None)
        ):
            return
        command = build_intruder_config_command(
            self.client.command_username, self.client.command_password
        )
        try:
            response = await async_retry_read_once(
                partial(self.client.async_send_flexml, command),
                description="reading intruder configuration",
            )
            self.state.intruder_config = parse_intruder_config(response)
        except FlexMLError as err:
            _LOGGER.info("READ_INTRUDER_CFG not available, skipping it: %s", err)
            self._intruder_config_unsupported = True
            return
        self._intruder_config_read_for = stamp
        try:
            response = await self.client.async_send_flexml(
                build_language_config_command(
                    self.client.command_username, self.client.command_password
                )
            )
            self.state.installed_languages = parse_installed_languages(response)
        except FlexMLError as err:
            _LOGGER.debug("READ_LANG_CFG not available: %s", err)

    async def async_set_calendar_week(
        self,
        calendar_id: int,
        week_type: int,
        days: dict[str, list[CalendarPeriod]],
    ) -> None:
        """Replace one week type of a calendar (sent once)."""
        async with self._client_operation_lock:
            await self.client.async_ensure_connected()
            command = build_edit_calendar_week_command(
                calendar_id,
                week_type,
                days,
                self.client.command_username,
                self.client.command_password,
            )
            response = await self.client.async_send_flexml(command)
            parse_simple_reply(response, "EDIT_CALENDAR_WEEK")
            await self._async_save_config_locked()
            await self._async_read_calendars_locked(force=True)
        self.async_set_updated_data(self.state)

    async def async_set_calendar(self, calendar: Any) -> None:
        """Replace a calendar's name and week types (sent once).

        EDIT_CALENDAR clears the times of all three week types on the panel
        (seen on an SPC4300, 3.14.1), so the times read before are sent back
        with EDIT_CALENDAR_WEEK before the configuration is saved.
        """
        async with self._client_operation_lock:
            await self.client.async_ensure_connected()
            command = build_edit_calendar_command(
                calendar, self.client.command_username, self.client.command_password
            )
            response = await self.client.async_send_flexml(command)
            parse_simple_reply(response, "EDIT_CALENDAR")
            for week_type in (1, 2, 3):
                days = {
                    day: list(calendar.weeks.get(week_type, {}).get(day, []))
                    for day in CALENDAR_DAYS
                }
                response = await self.client.async_send_flexml(
                    build_edit_calendar_week_command(
                        calendar.calendar_id,
                        week_type,
                        days,
                        self.client.command_username,
                        self.client.command_password,
                    )
                )
                parse_simple_reply(response, "EDIT_CALENDAR_WEEK")
            await self._async_save_config_locked()
            await self._async_read_calendars_locked(force=True)
        self.async_set_updated_data(self.state)

    async def async_add_calendar(
        self,
        calendar_id: int,
        name: str,
        week_types: str,
        weeks: dict[int, dict[str, list[CalendarPeriod]]],
    ) -> None:
        """Add a calendar with its week times (ADD_CALENDAR, weeks, SAVE_CONFIG)."""
        async with self._client_operation_lock:
            await self.client.async_ensure_connected()
            response = await self.client.async_send_flexml(
                build_add_calendar_command(
                    calendar_id,
                    name,
                    week_types,
                    self.client.command_username,
                    self.client.command_password,
                )
            )
            parse_simple_reply(response, "ADD_CALENDAR")
            for week_type in (1, 2, 3):
                days = {
                    day: list(weeks.get(week_type, {}).get(day, []))
                    for day in CALENDAR_DAYS
                }
                response = await self.client.async_send_flexml(
                    build_edit_calendar_week_command(
                        calendar_id,
                        week_type,
                        days,
                        self.client.command_username,
                        self.client.command_password,
                    )
                )
                parse_simple_reply(response, "EDIT_CALENDAR_WEEK")
            await self._async_save_config_locked()
            await self._async_read_calendars_locked(force=True)
        self.async_set_updated_data(self.state)

    async def async_set_calendar_exception(self, exception: Any, add: bool) -> None:
        """Add or replace an exception day (ADD/EDIT_CALEX + SAVE_CONFIG)."""
        await self._async_send_panel_command(
            build_calendar_exception_command(
                exception,
                add,
                self.client.command_username,
                self.client.command_password,
            ),
            "ADD_CALEX" if add else "EDIT_CALEX",
            save=True,
        )
        async with self._client_operation_lock:
            await self._async_read_calendars_locked(force=True)
        self.async_set_updated_data(self.state)

    async def async_delete_calendar_exception(self, exception_id: int) -> None:
        """Delete an exception day (DELETE_CALEX + SAVE_CONFIG)."""
        await self._async_send_panel_command(
            build_delete_calendar_exception_command(
                exception_id, self.client.command_username, self.client.command_password
            ),
            "DELETE_CALEX",
            save=True,
        )
        async with self._client_operation_lock:
            self.state.calendar_exceptions.pop(exception_id, None)
            await self._async_read_calendars_locked(force=True)
        self.async_set_updated_data(self.state)

    async def async_delete_calendar(self, calendar_id: int) -> None:
        """Delete a calendar (DELETE_CALENDAR + SAVE_CONFIG).

        Doors, areas or profiles that use it may lose that setting.
        """
        await self._async_send_panel_command(
            build_delete_calendar_command(
                calendar_id, self.client.command_username, self.client.command_password
            ),
            "DELETE_CALENDAR",
            save=True,
        )
        async with self._client_operation_lock:
            self.state.calendars.pop(calendar_id, None)
            await self._async_read_calendars_locked(force=True)
        self.async_set_updated_data(self.state)

    @property
    def _panel_status_unsupported(self) -> bool:
        """True when CMD_STATUS_PANEL answered "not available" in this session."""
        generation = getattr(self, "_panel_status_unsupported_generation", None)
        return generation is not None and generation == self.client.session_generation

    @_panel_status_unsupported.setter
    def _panel_status_unsupported(self, value: bool) -> None:
        self._panel_status_unsupported_generation = (
            self.client.session_generation if value else None
        )

    async def _async_read_panel_status_locked(self) -> None:
        """Read CMD_STATUS_PANEL (system alerts, Ethernet); best effort.

        Called with the client operation lock held. A panel or command
        profile that does not allow the command only loses these entities.
        """
        if getattr(self, "_panel_status_unsupported", False):
            return
        command = build_status_panel_command(
            self.client.command_username, self.client.command_password
        )
        try:
            response = await async_retry_read_once(
                partial(self.client.async_send_flexml, command),
                description="reading panel status",
            )
            status = parse_status_panel(response)
        except FlexMLError as err:
            if is_status_panel_unsupported(err):
                _LOGGER.info(
                    "CMD_STATUS_PANEL not available, skipping it until the next "
                    "FlexC session: %s",
                    err,
                )
                self._panel_status_unsupported = True
            else:
                _LOGGER.debug("Ignoring unreadable CMD_STATUS_PANEL reply: %s", err)
            return
        self.state.system_alerts = status.alerts
        self.state.ethernet = status.ethernet

    def _schedule_panel_status_refresh(self) -> None:
        """Read the system alerts again soon after a panel fault event.

        The system alert entities follow CMD_STATUS_PANEL, which is otherwise
        read once a minute. Only one read is queued at a time.
        """
        if not self.state.system_alerts or getattr(
            self, "_panel_status_unsupported", False
        ):
            return
        task = getattr(self, "_panel_status_refresh_task", None)
        if task is not None and not task.done():
            return
        self._panel_status_refresh_task = self.hass.async_create_background_task(
            self._async_refresh_panel_status(),
            f"{DOMAIN} panel status after fault event",
        )

    async def _async_refresh_panel_status(self) -> None:
        """Read CMD_STATUS_PANEL now and publish the new state."""
        try:
            async with self._client_operation_lock:
                await self._async_read_panel_status_locked()
        except Exception as err:  # noqa: BLE001 - best effort, polled again later
            _LOGGER.debug("Panel status read after fault event failed: %s", err)
            return
        self.async_set_updated_data(self.state)

    async def async_read_log(
        self, kind: str, object_id: int | None = None, sub_id: int | None = None
    ) -> list[dict[str, Any]]:
        """Read one panel log (read-only); records are returned newest first."""
        async with self._client_operation_lock:
            await self.client.async_ensure_connected()
            command = build_log_command(
                kind,
                object_id,
                self.client.command_username,
                self.client.command_password,
                sub_id,
            )
            response = await async_retry_read_once(
                partial(self.client.async_send_flexml, command),
                description=f"reading the {kind} log",
            )
        return parse_log(response, kind, dt_util.get_default_time_zone())

    async def _async_keep_clock_right_locked(self) -> None:
        """Set the panel clock when it drifted (option, default on; lock held)."""
        if not self.entry.options.get(CONF_CLOCK_SYNC, True):
            return
        offset = self.state.panel.clock_offset
        if offset is None or abs(offset) <= CLOCK_SYNC_LIMIT:
            return
        now = time.monotonic()
        if now - getattr(self, "_clock_synced_at", -1e9) < CLOCK_SYNC_INTERVAL:
            return
        self._clock_synced_at = now
        local_time = dt_util.now()
        try:
            response = await self.client.async_send_flexml(
                build_set_clock_command(
                    local_time,
                    self.client.command_username,
                    self.client.command_password,
                )
            )
            parse_simple_reply(response, "SET_CLOCK")
        except (FlexCError, FlexMLError) as err:
            _LOGGER.warning("Could not set the SPC panel clock: %s", err)
            return
        _LOGGER.info(
            "SPC panel clock was %+d s off; set to %s", offset, local_time.isoformat()
        )
        self.state.panel.clock_offset = 0

    async def async_set_panel_clock(self) -> None:
        """Set the panel clock to Home Assistant's local time (sent once)."""
        async with self._client_operation_lock:
            await self.client.async_ensure_connected()
            local_time = dt_util.now()
            command = build_set_clock_command(
                local_time, self.client.command_username, self.client.command_password
            )
            response = await self.client.async_send_flexml(command)
        parse_simple_reply(response, "SET_CLOCK")
        _LOGGER.info("SPC panel clock set to %s", local_time.isoformat())
        await self.async_request_refresh()

    async def async_clear_all_alerts(self) -> None:
        """Clear all system alerts on the panel (sent once)."""
        async with self._client_operation_lock:
            await self.client.async_ensure_connected()
            command = build_clear_all_alerts_command(
                self.client.command_username, self.client.command_password
            )
            response = await self.client.async_send_flexml(command)
        parse_simple_reply(response, "CLEAR_ALL_ALERTS")
        _LOGGER.info("SPC panel alerts cleared")
        await self.async_request_refresh()

    async def _async_save_config_locked(self) -> None:
        """Save the panel configuration right after a change (lock held).

        Without it the panel restarts and drops the change (see
        build_save_config_command).
        """
        response = await self.client.async_send_flexml(
            build_save_config_command(
                self.client.command_username, self.client.command_password
            )
        )
        parse_simple_reply(response, "SAVE_CONFIG")
        _LOGGER.info("SPC configuration saved")

    async def _async_send_panel_command(
        self, command: str, name: str, *, save: bool = False
    ) -> None:
        """Send one state-changing command once and check its reply.

        ``save`` sends SAVE_CONFIG after a configuration change.
        """
        async with self._client_operation_lock:
            await self.client.async_ensure_connected()
            response = await self.client.async_send_flexml(command)
            parse_simple_reply(response, name)
            if save:
                await self._async_save_config_locked()

    async def async_silence_bells(self) -> None:
        """Silence all bells (CMD_SILENCE_ALL_BELLS). UNTESTED on a panel."""
        await self._async_send_panel_command(
            build_silence_all_bells_command(
                self.client.command_username, self.client.command_password
            ),
            "SILENCE_ALL_BELLS",
        )
        _LOGGER.info("SPC bells silenced")

    async def async_request_flexc_test(self, ats_id: int, atp_seq_id: int) -> None:
        """Ask the panel for a FlexC test call on one ATP. UNTESTED on a panel."""
        await self._async_send_panel_command(
            build_flexc_manual_test_command(
                ats_id,
                atp_seq_id,
                self.client.command_username,
                self.client.command_password,
            ),
            "REQUEST_FLEXC_MANUAL_TEST",
        )
        _LOGGER.info("SPC FlexC test call requested: ATS %d ATP %d", ats_id, atp_seq_id)

    async def async_alert_control(self, alert_key: str, action: int) -> None:
        """Inhibit/isolate (or undo) one system alert.

        ALERT_ID is the alert's SYSALERT bit number, not the alert number of
        the panel's alert list (checked 2026-11-13: the network fault is
        ALERT_ID="24"; "38" answers 75). ACTION 0 inhibit, 1 de-inhibit,
        2 isolate, 3 de-isolate, all checked on the network fault.

        The command is sent once. CMD_STATUS_PANEL is then read again; if the
        alert's mask did not change as expected, an error is raised so that a
        wrong guess of the command's attributes never looks like success.
        """
        alert = next((a for a in SYSTEM_ALERTS if a.key == alert_key), None)
        if alert is None:
            raise ValueError(f"Unknown system alert {alert_key}")
        command = build_alert_control_command(
            alert.bit,
            action,
            self.client.command_username,
            self.client.command_password,
        )
        async with self._client_operation_lock:
            await self.client.async_ensure_connected()
            response = await self.client.async_send_flexml(command)
            parse_simple_reply(response, "ALERT_CONTROL")
            self._panel_status_unsupported = False
            await self._async_read_panel_status_locked()
        self.async_set_updated_data(self.state)
        state = self.state.system_alerts.get(alert_key)
        if action in (ALERT_ACTION_INHIBIT, ALERT_ACTION_INHIBIT + 1):
            expected, actual = (
                action == ALERT_ACTION_INHIBIT,
                getattr(state, "inhibited", None),
            )
        else:
            expected, actual = (
                action == ALERT_ACTION_ISOLATE,
                getattr(state, "isolated", None),
            )
        if actual is not expected:
            raise FlexMLError(
                f"ALERT_CONTROL action {action} for alert {alert.alert_id} was "
                "accepted but the panel status did not change"
            )

    def engineer_credentials(self) -> tuple[str, str] | None:
        """The engineer login, or None when nobody is logged in.

        A login that is not remembered ends after ENGINEER_IDLE_LOGOUT
        seconds without use, like the web page, but never while the panel
        is in engineer mode (it is needed to leave it).
        """
        session = self._engineer
        if session is None:
            return None
        if (
            not session["remember"]
            and time.monotonic() - session["last_used"] > ENGINEER_IDLE_LOGOUT
            and not self.state.panel.engineer_mode
        ):
            self._engineer = None
            self._keep_engineer_session()
            _LOGGER.info("SPC engineer login ended after inactivity")
            return None
        return session["username"], session["password"]

    @property
    def has_engineer_login(self) -> bool:
        """Return whether an engineer (Programtekniker) is logged in."""
        return self.engineer_credentials() is not None

    @property
    def engineer_session(self) -> dict[str, Any]:
        """Who is logged in as engineer, for the UI (never the password)."""
        if self.engineer_credentials() is None or self._engineer is None:
            return {"logged_in": False}
        session = self._engineer
        return {
            "logged_in": True,
            "user_id": session["user_id"],
            "remembered": session["remember"],
            "idle_logout": None if session["remember"] else ENGINEER_IDLE_LOGOUT,
        }

    def _engineer_sessions(self) -> dict[str, dict[str, Any]]:
        """Engineer logins kept in memory across reloads, by config entry."""
        sessions: dict[str, dict[str, Any]] = self.hass.data.setdefault(
            f"{DOMAIN}_engineer_sessions", {}
        )
        return sessions

    def _keep_engineer_session(self) -> None:
        """Keep the current engineer login in memory for a reload, or drop it."""
        sessions = self._engineer_sessions()
        if self._engineer is None or self._engineer.get("remember"):
            sessions.pop(self.entry.entry_id, None)
        else:
            sessions[self.entry.entry_id] = self._engineer

    async def async_engineer_login(
        self, username: str, password: str, remember: bool
    ) -> None:
        """Log in as engineer: the panel must confirm ENGINEER="1".

        Sends only VERIFY_USER_ON_PANEL (a read). The password is stored in
        the config entry only when remember is set; otherwise it lives in
        memory until logout, restart or inactivity.
        """
        async with self._client_operation_lock:
            await self.client.async_ensure_connected()
            response = await self.client.async_send_flexml(
                build_verify_user_command(username, password)
            )
        login = parse_verify_user(response)
        if not login["engineer"]:
            raise FlexMLError("The login is not an engineer (Programtekniker)")
        self._engineer = {
            "username": username,
            "password": password,
            "remember": remember,
            "user_id": login["user_id"],
            "last_used": time.monotonic(),
        }
        self._store_engineer_login(username if remember else None, password)
        self._keep_engineer_session()
        _LOGGER.info("SPC engineer logged in (remembered: %s)", remember)
        self.async_update_listeners()

    async def async_engineer_logout(self) -> None:
        """Log out the engineer and forget a remembered password.

        Refused while the panel is in engineer mode: the login is needed to
        leave it, as on the web page.
        """
        if self.state.panel.engineer_mode:
            raise FlexMLError("Leave engineer mode before logging out")
        self._engineer = None
        self._store_engineer_login(None, None)
        self._keep_engineer_session()
        _LOGGER.info("SPC engineer logged out")
        self.async_update_listeners()

    def _store_engineer_login(self, username: str | None, password: str | None) -> None:
        """Remember or forget the engineer login in the config entry."""
        data = dict(self.entry.data)
        if username:
            data[CONF_ENGINEER_USERNAME] = username
            data[CONF_ENGINEER_PASSWORD] = password
        else:
            data.pop(CONF_ENGINEER_USERNAME, None)
            data.pop(CONF_ENGINEER_PASSWORD, None)
        if data != dict(self.entry.data):
            self.hass.config_entries.async_update_entry(self.entry, data=data)

    async def async_read_zone_config(self, zone_id: int) -> dict[str, str]:
        """Read one zone's whole configuration record (GET_ZONE_CONFIG)."""
        async with self._client_operation_lock:
            await self.client.async_ensure_connected()
            response = await self.client.async_send_flexml(
                build_get_zone_config_command(
                    zone_id, self.client.command_username, self.client.command_password
                )
            )
        return parse_zone_config(response, zone_id)

    async def async_edit_zone(self, zone_id: int, **changes: Any) -> dict[str, str]:
        """Change a zone's configuration (EDIT_ZONE + SAVE_CONFIG, sent once).

        Checked on the panel 2026-11-13: EDIT_ZONE needs the engineer login and
        installer mode and takes the whole record, so the record is read,
        changed and sent whole; the panel answers an accepted change with an
        empty reply. The record is read back after SAVE_CONFIG and a
        difference is reported as an error.
        """
        credentials = self.engineer_credentials()
        if credentials is None:
            raise FlexMLError(
                "Changing a zone needs the engineer login (log in as engineer first)"
            )
        if self.state.panel.engineer_mode is False:
            raise FlexMLError("Changing a zone needs the panel in installer mode")
        async with self._client_operation_lock:
            await self.client.async_ensure_connected()
            response = await self.client.async_send_flexml(
                build_get_zone_config_command(
                    zone_id, self.client.command_username, self.client.command_password
                )
            )
            record = parse_zone_config(response, zone_id)
            updated = apply_zone_changes(record, **changes)
            if all(updated[key] == record[key] for key in updated):
                return record
            response = await self.client.async_send_flexml(
                build_edit_zone_command(updated, *credentials)
            )
            parse_edit_zone_reply(response)
            await self._async_save_config_locked()
            response = await self.client.async_send_flexml(
                build_get_zone_config_command(
                    zone_id, self.client.command_username, self.client.command_password
                )
            )
            after = parse_zone_config(response, zone_id)
        if self._engineer is not None:
            self._engineer["last_used"] = time.monotonic()
        wrong = [key for key in updated if after.get(key) != updated[key]]
        if wrong:
            raise FlexMLError(f"Zone {zone_id} saved but reads back different {wrong}")
        _LOGGER.info("SPC zone %d configuration changed", zone_id)
        if after["NAME"] != record["NAME"] or after["AREA"] != record["AREA"]:
            # Names and areas are read at setup; our own SAVE_CONFIG does not
            # trigger the reload a change on the panel would.
            self.hass.config_entries.async_schedule_reload(self.entry.entry_id)
        else:
            await self.async_request_refresh()
        return after

    async def async_set_engineer_mode(self, enter: bool) -> None:
        """Enter or exit full engineer mode with the engineer login (sent once)."""
        credentials = self.engineer_credentials()
        if credentials is None:
            raise FlexMLError("No engineer is logged in")
        command_name = (
            "ENTER_FULL_ENGINEER_MODE" if enter else "EXIT_FULL_ENGINEER_MODE"
        )
        async with self._client_operation_lock:
            await self.client.async_ensure_connected()
            command = build_engineer_mode_command(enter, *credentials)
            response = await self.client.async_send_flexml(command)
        parse_simple_reply(response, command_name)
        if self._engineer is not None:
            self._engineer["last_used"] = time.monotonic()
        _LOGGER.info("SPC engineer mode %s", "entered" if enter else "exited")
        await self.async_request_refresh()

    async def async_restore_panel_tamper(self) -> None:
        """Restore last event-confirmed panel tamper state, if available."""
        try:
            saved = await self._tamper_store.async_load()
        except Exception:  # Storage failure must not prevent alarm integration setup.
            _LOGGER.exception("Could not restore last known panel tamper state")
            return
        if isinstance(saved, dict) and type(saved.get("panel_tamper")) is bool:
            self.state.faults.panel_tamper = saved["panel_tamper"]
            _LOGGER.debug("Restored last known panel tamper state")

    async def async_restore_area_history(self) -> None:
        """Restore persisted area history, never stale operating modes."""
        try:
            saved = await self._area_history_store.async_load()
        except Exception:
            _LOGGER.exception("Could not restore SPC area history")
            return
        if not isinstance(saved, dict):
            return
        for raw_id, value in saved.items():
            area_id = _int_value(raw_id)
            if area_id is None or not isinstance(value, dict):
                continue
            history: dict[str, Any] = {}
            for kind in ("arm", "disarm"):
                raw_time = value.get(f"last_{kind}_time")
                if not isinstance(raw_time, str):
                    continue
                try:
                    timestamp = datetime.fromisoformat(raw_time)
                except ValueError:
                    continue
                if timestamp.tzinfo is None:
                    continue
                history[f"last_{kind}_time"] = timestamp
                history[f"last_{kind}_user_id"] = _int_value(
                    value.get(f"last_{kind}_user_id")
                )
                name = value.get(f"last_{kind}_user_name")
                history[f"last_{kind}_user_name"] = (
                    name if isinstance(name, str) else None
                )
                history[f"last_{kind}_user_display_name"] = history[
                    f"last_{kind}_user_name"
                ]
            if history:
                self._area_history[area_id] = history

    def door_history(self, door_id: int) -> dict[str, Any]:
        """The door's last unlock and last opening (timestamps as ISO text)."""
        history = self._door_history.get(door_id, {})
        name = history.get("unlocked_user_name")
        own = (self.state.command_login or {}).get("user_id")
        if (
            own is not None
            and history.get("unlocked_user_id") == own
            and not str(name or "").startswith("Home Assistant")
        ):
            # Saved before the integration knew its own login: name it now.
            name = "Home Assistant"
        return {
            "last_unlocked": _iso(history.get("unlocked_at")),
            "last_unlocked_by": history.get("unlocked_by"),
            "last_unlocked_user_id": history.get("unlocked_user_id"),
            "last_unlocked_user_name": name,
            "last_opened": _iso(history.get("opened_at")),
        }

    def note_door_unlocked(
        self,
        door_id: int,
        when: datetime,
        how: str,
        user_id: int | None = None,
        user_name: str | None = None,
    ) -> None:
        """Remember an unlock if it is the newest one for the door."""
        history = self._door_history.setdefault(door_id, {})
        previous = history.get("unlocked_at")
        if isinstance(previous, datetime) and (
            previous > when
            or (
                previous == when
                # The same second: who unlocked wins over the exit button.
                and not (
                    history.get("unlocked_by") == "exit_button" and how != "exit_button"
                )
            )
        ):
            return
        history.update(
            unlocked_at=when,
            unlocked_by=how,
            unlocked_user_id=user_id,
            unlocked_user_name=user_name,
        )
        self._door_history_store.async_delay_save(self._save_door_history, 1)

    HA_REQUEST_WINDOW = 30.0

    def note_ha_door_request(self, door_id: int, ha_user: str | None) -> None:
        """Remember that a door command was sent from Home Assistant now."""
        self._ha_door_requests[door_id] = (time.monotonic(), ha_user)

    def unlocker_name(
        self, user_id: int | None, user_name: str | None, door_id: int | None = None
    ) -> str | None:
        """The name to show for who unlocked a door.

        The panel reports commands from this integration with its own login
        (on the reference panel user 9995 "Kommandoprofilan"); show that as
        Home Assistant, with the Home Assistant user when the command was sent
        from here moments before.
        """
        own = (self.state.command_login or {}).get("user_id")
        if user_id is None or own is None or user_id != own:
            return user_name
        request = self._ha_door_requests.get(door_id) if door_id is not None else None
        if (
            request
            and time.monotonic() - request[0] < self.HA_REQUEST_WINDOW
            and request[1]
        ):
            return f"Home Assistant ({request[1]})"
        return "Home Assistant"

    def note_door_opened(self, door_id: int, when: datetime) -> None:
        """Remember that the door was opened (someone passed)."""
        history = self._door_history.setdefault(door_id, {})
        previous = history.get("opened_at")
        if isinstance(previous, datetime) and previous >= when:
            return
        history["opened_at"] = when
        self._door_history_store.async_delay_save(self._save_door_history, 1)

    def _save_door_history(self) -> dict[str, Any]:
        return {
            str(door_id): {
                key: value.isoformat() if isinstance(value, datetime) else value
                for key, value in history.items()
            }
            for door_id, history in self._door_history.items()
        }

    async def async_restore_door_history(self) -> None:
        """Load the doors' last unlock and opening saved before a restart."""
        try:
            saved = await self._door_history_store.async_load()
        except Exception:  # Storage failure must not prevent setup.
            _LOGGER.exception("Could not restore SPC door history")
            return
        if not isinstance(saved, dict):
            return
        for raw_id, value in saved.items():
            door_id = _int_value(raw_id)
            if door_id is None or not isinstance(value, dict):
                continue
            history: dict[str, Any] = {}
            for key, item in value.items():
                if key.endswith("_at") and isinstance(item, str):
                    parsed = dt_util.parse_datetime(item)
                    if parsed is not None:
                        history[key] = parsed
                elif (
                    key in ("unlocked_by", "unlocked_user_name")
                    and isinstance(item, str)
                    or key == "unlocked_user_id"
                    and isinstance(item, int)
                ):
                    history[key] = item
            self._door_history[door_id] = history

    def _save_area_history(self) -> dict[str, Any]:
        """Persist timestamps and identities only, never raw event data."""
        saved: dict[str, Any] = {}
        for area_id, history in self._area_history.items():
            item: dict[str, Any] = {}
            for kind in ("arm", "disarm"):
                timestamp = history.get(f"last_{kind}_time")
                if not isinstance(timestamp, datetime):
                    continue
                item[f"last_{kind}_time"] = timestamp.isoformat()
                item[f"last_{kind}_user_id"] = history.get(f"last_{kind}_user_id")
                item[f"last_{kind}_user_name"] = history.get(f"last_{kind}_user_name")
            if item:
                saved[str(area_id)] = item
        return saved

    def _display_user_name(
        self, user_id: int | None, raw_name: str | None
    ) -> str | None:
        """Apply user aliases without changing the raw SPC identity."""
        return display_user_name(
            user_id,
            raw_name,
            self.entry.options.get(CONF_USER_ALIASES, {}),
            self._user_names,
        )

    def _merge_area_history(self, area: AreaState) -> None:
        """Retain event history when area polling rebuilds the state object."""
        history = self._area_history.get(area.area_id, {})
        for kind in ("arm", "disarm"):
            history[f"last_{kind}_user_display_name"] = self._display_user_name(
                history.get(f"last_{kind}_user_id"),
                history.get(f"last_{kind}_user_name"),
            )
            for suffix in ("time", "user_id", "user_name", "user_display_name"):
                field = f"last_{kind}_{suffix}"
                if field in history:
                    setattr(area, field, history[field])

    def _apply_area_history_event(self, event: dict[str, str]) -> bool:
        """Track arm/disarm events without accepting duplicates or stale events."""
        event_id = _int_value(event.get("EV_ID"))
        area_id = _int_value(event.get("AREA_ID"))
        if event_id not in (3501, 3502, 3503, 3504) or area_id is None:
            return False
        area = self.state.areas.get(area_id)
        if area is None:
            return False
        timestamp = _spc_datetime(
            event.get("TIMESTAMP"), dt_util.get_default_time_zone()
        )
        if timestamp is None:
            return False
        history = self._area_history.setdefault(area_id, {})
        timestamps = [
            history.get(field) for field in ("last_arm_time", "last_disarm_time")
        ]
        newest = max(
            (value for value in timestamps if isinstance(value, datetime)),
            default=None,
        )
        if newest is not None and timestamp <= newest:
            return False
        kind = "disarm" if event_id == 3501 else "arm"
        user_name = event.get("USER_NAME") or None
        history.update(
            {
                f"last_{kind}_time": timestamp,
                f"last_{kind}_user_id": _int_value(event.get("USER_ID")),
                f"last_{kind}_user_name": user_name,
                f"last_{kind}_user_display_name": self._display_user_name(
                    _int_value(event.get("USER_ID")), user_name
                ),
            }
        )
        self._merge_area_history(area)
        self._area_history_store.async_delay_save(self._save_area_history, 1)
        return True

    def _handle_session_ready(self, generation: int) -> None:
        """Schedule state reconciliation after a replacement FlexC session."""
        if self._activity_seen is None:
            # Remember what the panel logs already hold, so only new lines show.
            self.schedule_activity_log_read(20.0)
        if not self._discovery_requested or not self._discovery_complete:
            return
        self._pending_reconcile_generation = max(
            self._pending_reconcile_generation, generation
        )
        if (
            self._reconnect_reconcile_task is not None
            and not self._reconnect_reconcile_task.done()
        ):
            return
        self._reconnect_reconcile_task = self.entry.async_create_background_task(
            self.hass,
            self._async_reconcile_after_reconnect(),
            name=f"{DOMAIN} reconnect reconciliation",
            eager_start=False,
        )

    async def _async_reconcile_after_reconnect(self) -> None:
        """Refresh known live state after the SPC establishes a new session."""
        try:
            while self._pending_reconcile_generation > self._last_reconciled_generation:
                generation = self._pending_reconcile_generation
                started = asyncio.get_running_loop().time()
                _LOGGER.info(
                    "FlexC state reconciliation started after connection #%d",
                    generation,
                )
                try:
                    async with self._client_operation_lock:
                        await self.client.async_ensure_connected()
                        changed = await self._async_reconcile_known_state_locked()
                except asyncio.CancelledError:
                    raise
                except (FlexCError, FlexMLError) as err:
                    _LOGGER.warning(
                        "FlexC state reconciliation for connection #%d was interrupted: %s",
                        generation,
                        err,
                    )
                    return

                if self._pending_reconcile_generation != generation:
                    _LOGGER.info(
                        "FlexC state reconciliation for connection #%d completed "
                        "after connection #%d became ready; a fresh reconciliation "
                        "will follow",
                        generation,
                        self._pending_reconcile_generation,
                    )
                self._last_reconciled_generation = generation
                if changed:
                    self.async_set_updated_data(self.state)
                elapsed = asyncio.get_running_loop().time() - started
                _LOGGER.info(
                    "FlexC state reconciliation completed after connection #%d "
                    "in %.3fs (changed=%s)",
                    generation,
                    elapsed,
                    changed,
                )
        finally:
            self._reconnect_reconcile_task = None
            if self._pending_reconcile_generation > self._last_reconciled_generation:
                self._handle_session_ready(self._pending_reconcile_generation)

    async def _async_reconcile_known_state_locked(self) -> bool:
        """Refresh known base states while the shared operation lock is held."""
        changed = False
        timezone = dt_util.get_default_time_zone()

        if self._area_discovery_complete and self._detected_area_ids:
            area_ids = sorted(self._detected_area_ids)
            raw_areas = await async_retry_read_once(
                lambda: self.client.async_get_area_status(area_ids),
                description="reconciling areas after reconnect",
            )
            for raw_area in raw_areas:
                area = _area_state_from_status(raw_area, timezone)
                previous_area = self.state.areas.get(area.area_id)
                if previous_area is not None:
                    # Some reconnect responses omit history attributes. Absence
                    # does not mean the panel cleared its previous history.
                    history_fields = {
                        "LAST_SET_TIME": "last_set_time",
                        "LAST_SET_USER_ID": "last_set_user_id",
                        "LAST_SET_USER_NAME": "last_set_user_name",
                        "LAST_UNSET_TIME": "last_unset_time",
                        "LAST_UNSET_USER_ID": "last_unset_user_id",
                        "LAST_UNSET_USER_NAME": "last_unset_user_name",
                        "LAST_ALARM": "last_alarm",
                    }
                    for raw_key, field_name in history_fields.items():
                        if raw_key not in raw_area and raw_key in previous_area.raw:
                            area.raw[raw_key] = previous_area.raw[raw_key]
                            setattr(
                                area, field_name, getattr(previous_area, field_name)
                            )
                if previous_area is None or previous_area.raw != area.raw:
                    if previous_area is None:
                        _LOGGER.info(
                            "Area %d discovered during reconnect", area.area_id
                        )
                    else:
                        changes = _area_reconciliation_changes(
                            previous_area.raw, area.raw
                        )
                        _LOGGER.info(
                            "Area %d reconciliation after reconnect: %s",
                            area.area_id,
                            ", ".join(changes),
                        )
                    changed = True
                self._reconcile_area_intrusion(area, previous_area)
                self._merge_area_history(area)
                self.state.areas[area.area_id] = area

        if self._zone_discovery_complete and self._detected_zone_ids:
            zone_ids = sorted(self._detected_zone_ids)
            for index in range(0, len(zone_ids), ZONE_POLL_BATCH_SIZE):
                batch = zone_ids[index : index + ZONE_POLL_BATCH_SIZE]
                raw_zones = await async_retry_read_once(
                    partial(self.client.async_get_zone_status, batch),
                    description=f"reconciling zones {batch[0]}..{batch[-1]} after reconnect",
                )
                for raw_zone in raw_zones:
                    zone = _zone_state_from_status(raw_zone)
                    previous_zone = self.state.zones.get(zone.zone_id)
                    event_changed = _reconcile_zone_event_state(zone, previous_zone)
                    if (
                        previous_zone is None
                        or previous_zone.raw != zone.raw
                        or event_changed
                    ):
                        changed = True
                    self.state.zones[zone.zone_id] = zone

        if self._xbus_discovery_complete:
            raw_devices = await async_retry_read_once(
                partial(async_get_xbus_status, self.client),
                description="reconciling X-BUS devices after reconnect",
            )
            seen_serials: set[str] = set()
            for raw_device in raw_devices:
                serial = raw_device.get("SN")
                if not serial:
                    continue
                previous_xbus = self.state.xbus_devices.get(serial)
                device = _xbus_device_state_from_status(raw_device, previous_xbus)
                if device is None:
                    continue
                seen_serials.add(serial)
                if previous_xbus is None or previous_xbus.raw != device.raw:
                    changed = True
                self.state.xbus_devices[serial] = device
            missing_serials = set(self.state.xbus_devices) - seen_serials
            for serial in missing_serials:
                del self.state.xbus_devices[serial]
                changed = True
            if seen_serials != self._detected_xbus_serials:
                self._detected_xbus_serials = seen_serials
                changed = True

        return changed

    async def _async_update_data(self) -> SpcState:
        try:
            async with self._client_operation_lock:
                await self.client.async_ensure_connected()
                summary = await async_retry_read_once(
                    self.client.async_get_panel_summary,
                    description="reading panel summary",
                )
                if summary:
                    previous_config = self.state.panel.configuration_changed
                    self.state.panel = _panel_state_from_summary(
                        summary, dt_util.get_default_time_zone()
                    )
                    self._check_configuration_change(previous_config)
                    await self._async_keep_clock_right_locked()
                alerts = await async_retry_read_once(
                    self.client.async_get_alert_status,
                    description="reading panel alerts",
                )
                self.state.alerts = [
                    {
                        "event_id": _int_value(alert.get("EV_ID")),
                        "state": _int_value(alert.get("STATE")),
                    }
                    for alert in alerts
                ]
                await self._async_read_panel_status_locked()
                await self._async_read_calendars_locked()
                await self._async_read_intruder_config_locked()
                await self._async_read_users_locked()
                await self._async_read_user_profiles_locked()
                await self._async_check_login_locked()
                await self._async_read_wireless_locked()
                await self._async_read_unknown_cards_locked()
                if not alerts:
                    self.state.faults.modem_1_fault = False
                    self.state.faults.modem_1_line_fault = False
                    self.state.faults.rf_jamming = False
                    self.state.faults.xbus_battery_fault = False
                    self.state.faults.xbus_mains_fault = False
                timezone = dt_util.get_default_time_zone()
                if self._ats_discovery_complete:
                    for ats_id in sorted(self._detected_ats_ids):
                        try:
                            ats_status = await async_retry_read_once(
                                partial(self.client.async_get_flexc_ats_status, ats_id),
                                description=f"reading ATS {ats_id}",
                            )
                        except FlexMLError as err:
                            _LOGGER.debug(
                                "Ignoring unavailable previously detected FlexC ATS %d: %s",
                                ats_id,
                                err,
                            )
                            continue
                        if ats_status:
                            ats = _ats_state_from_status(ats_status, timezone)
                            self.state.ats[ats.ats_id] = ats
                if self._area_discovery_complete and self._detected_area_ids:
                    area_ids = sorted(self._detected_area_ids)
                    raw_areas = await async_retry_read_once(
                        lambda: self.client.async_get_area_status(area_ids),
                        description="reading area status",
                    )
                    for raw_area in raw_areas:
                        area = _area_state_from_status(raw_area, timezone)
                        previous = self.state.areas.get(area.area_id)
                        if previous is not None and previous.mode != area.mode:
                            _LOGGER.warning(
                                "SPC area reconciliation changed mode: area_id=%d name=%r %s -> %s",
                                area.area_id,
                                area.name,
                                previous.mode,
                                area.mode,
                            )
                        self._reconcile_area_intrusion(area, previous)
                        self._merge_area_history(area)
                        self.state.areas[area.area_id] = area

            if self._discovery_requested and not self._discovery_complete:
                self._schedule_discovery()
            return self.state
        except FlexCError as err:
            raise UpdateFailed(f"FlexC update failed: {err}") from err

    @property
    def _discovery_complete(self) -> bool:
        return (
            self._ats_discovery_complete
            and self._area_discovery_complete
            and self._zone_discovery_complete
            and self._door_discovery_complete
            and self._xbus_discovery_complete
        )

    def async_start_background_discovery(self) -> None:
        self._discovery_requested = True
        self._schedule_discovery()

    def _schedule_discovery(self) -> None:
        if self._discovery_complete:
            return
        if self._discovery_task is not None and not self._discovery_task.done():
            return
        self._discovery_task = self.entry.async_create_background_task(
            self.hass,
            self._async_discover_panel_objects(),
            name=f"{DOMAIN} discovery",
            eager_start=False,
        )

    async def _async_discover_panel_objects(self) -> None:
        try:
            timezone = dt_util.get_default_time_zone()
            async with self._client_operation_lock:
                await self.client.async_ensure_connected()
                detected_ats_ids: set[int] = set()
                for ats_id in ATS_IDS:
                    try:
                        ats_status = await async_retry_read_once(
                            partial(self.client.async_get_flexc_ats_status, ats_id),
                            description=f"discovering ATS {ats_id}",
                        )
                    except FlexMLError as err:
                        _LOGGER.debug("FlexC ATS %d not detected: %s", ats_id, err)
                        continue
                    if ats_status:
                        ats = _ats_state_from_status(ats_status, timezone)
                        self.state.ats[ats.ats_id] = ats
                        detected_ats_ids.add(ats.ats_id)
                self._detected_ats_ids.update(detected_ats_ids)
                self._ats_discovery_complete = True
                # X-BUS first: zones and doors are placed on its hardware.
                detected_xbus_serials: set[str] = set()
                raw_xbus_devices = await async_retry_read_once(
                    partial(async_get_xbus_status, self.client),
                    description="discovering X-BUS devices",
                )
                for raw_device in raw_xbus_devices:
                    serial = raw_device.get("SN")
                    if not serial:
                        _LOGGER.warning(
                            "Ignoring X-BUS ENETNODE without a serial number: %s",
                            raw_device,
                        )
                        continue
                    previous = self.state.xbus_devices.get(serial)
                    device = _xbus_device_state_from_status(raw_device, previous)
                    if device is None:
                        continue
                    self.state.xbus_devices[serial] = device
                    detected_xbus_serials.add(serial)
                self._detected_xbus_serials = detected_xbus_serials
                self._xbus_discovery_complete = True
                detected_area_ids: set[int] = set()
                raw_areas = await async_retry_read_once(
                    lambda: async_discover_areas(self.client, AREA_DISCOVERY_MAX_ID),
                    description="discovering areas",
                )
                for raw_area in raw_areas:
                    area = _area_state_from_status(raw_area, timezone)
                    self._merge_area_history(area)
                    self.state.areas[area.area_id] = area
                    detected_area_ids.add(area.area_id)
                self._detected_area_ids.update(detected_area_ids)
                self._area_discovery_complete = True
                detected_zone_ids: set[int] = set()
                raw_zones = await async_retry_read_once(
                    lambda: async_discover_zones(self.client, ZONE_DISCOVERY_MAX_ID),
                    description="discovering zones",
                )
                for raw_zone in raw_zones:
                    zone = _zone_state_from_status(raw_zone)
                    self.state.zones[zone.zone_id] = zone
                    detected_zone_ids.add(zone.zone_id)
                self._detected_zone_ids.update(detected_zone_ids)
                self._zone_discovery_complete = True
                detected_door_ids: set[int] = set()
                raw_doors = await async_retry_read_once(
                    lambda: async_discover_doors(self.client, DOOR_DISCOVERY_MAX_ID),
                    description="discovering doors",
                )
                for raw_door in raw_doors:
                    door = door_state_from_status(
                        raw_door,
                        self.state.doors.get(int(raw_door["DOOR_ID"])),
                        self.state.areas,
                    )
                    self.state.doors[door.door_id] = door
                    detected_door_ids.add(door.door_id)
                self._detected_door_ids.update(detected_door_ids)
                self._door_discovery_complete = True
                # Resolve only users referenced by restored events; do not scan
                # the whole user database or persist sensitive user configuration.
                known_user_ids = {
                    user_id
                    for history in self._area_history.values()
                    for kind in ("arm", "disarm")
                    if isinstance((user_id := history.get(f"last_{kind}_user_id")), int)
                    and 1 <= user_id <= 9999
                }
                for user_id in sorted(known_user_ids):
                    try:
                        name = await self.client.async_get_user_name(user_id)
                    except (FlexCError, FlexMLError, ValueError):
                        # Responses may contain private fields: never log them.
                        continue
                    if name:
                        self._user_names[user_id] = name
                for area in self.state.areas.values():
                    self._merge_area_history(area)
            _LOGGER.info(
                "FlexC discovery completed: ATS=%s areas=%s zones=%s doors=%s X-BUS=%s",
                sorted(self._detected_ats_ids),
                sorted(self._detected_area_ids),
                sorted(self._detected_zone_ids),
                sorted(self._detected_door_ids),
                sorted(self._detected_xbus_serials),
            )
            self.async_set_updated_data(self.state)
            self._schedule_zone_polling()
            self._schedule_xbus_polling()
        except asyncio.CancelledError:
            raise
        except (FlexCError, FlexMLError) as err:
            _LOGGER.debug("FlexC background discovery interrupted: %s", err)
        finally:
            current_task = asyncio.current_task()
            if self._discovery_task is current_task:
                self._discovery_task = None

    def _should_run_polling(self) -> bool:
        """Allow polling only while discovery is active and HA is running."""
        return self._discovery_requested and self.hass.state not in (
            CoreState.stopping,
            CoreState.stopped,
        )

    def _schedule_zone_polling(self) -> None:
        if not self._should_run_polling():
            return
        if not self._zone_discovery_complete or not self._detected_zone_ids:
            return
        if self._zone_poll_task is not None and not self._zone_poll_task.done():
            return
        self._zone_poll_task = self.entry.async_create_background_task(
            self.hass,
            self._async_zone_poll_loop(),
            name=f"{DOMAIN} zone polling",
            eager_start=False,
        )

    async def _async_zone_poll_loop(self) -> None:
        """Poll zones without allowing one malformed reply to stop live updates."""
        _LOGGER.debug("SPC zone polling started")
        previous_poll_started: float | None = None
        poll_loop_started = asyncio.get_running_loop().time()
        try:
            while True:
                await asyncio.sleep(
                    poll_delay_for_phase(ZONE_POLL_PHASE, ZONE_POLL_INTERVAL)
                )
                if not self._zone_discovery_complete:
                    continue
                zone_ids = sorted(self._detected_zone_ids)
                if not zone_ids:
                    continue
                try:
                    # Temporary beta timing diagnostics; no scheduling changes.
                    clock = asyncio.get_running_loop()
                    poll_started = clock.time()
                    interval_ms = (
                        (poll_started - previous_poll_started) * 1000
                        if previous_poll_started is not None
                        else None
                    )
                    previous_poll_started = poll_started
                    raw_zones: list[dict[str, str]] = []
                    poll_event_generations: dict[int, int] = {}
                    batch_timings: list[tuple[int, int, float]] = []
                    # Release the coordinator operation lock between batches
                    # so area/door/user commands are not queued behind an
                    # entire zone scan. Each individual batch remains atomic.
                    lock_wait_total_ms = 0.0
                    resync_wait_total_ms = 0.0
                    for index in range(0, len(zone_ids), ZONE_POLL_BATCH_SIZE):
                        batch = zone_ids[index : index + ZONE_POLL_BATCH_SIZE]
                        # A spontaneous EVENT invalidates the command context.
                        # Wait for the next SPC POLL *before* taking the shared
                        # coordinator lock, so other tasks are not blocked by
                        # this zone poll while the transport resynchronizes.
                        # The command layer rechecks the context under its own
                        # lock to handle races with newer EVENTs.
                        resync_wait_total_ms += (
                            await self.client.async_wait_for_event_resync()
                        )
                        waiting_since = clock.time()
                        async with self._client_operation_lock:
                            lock_wait_total_ms += (clock.time() - waiting_since) * 1000
                            await self.client.async_ensure_connected()
                            request_started = clock.time()
                            generations_before_read = {
                                zone_id: self._pir_event_generation.get(zone_id, 0)
                                for zone_id in batch
                            }
                            batch_zones = await async_retry_read_once(
                                partial(self.client.async_get_zone_status, batch),
                                description=f"polling zones {batch[0]}..{batch[-1]}",
                            )
                            batch_timings.append(
                                (
                                    batch[0],
                                    batch[-1],
                                    (clock.time() - request_started) * 1000,
                                )
                            )
                            raw_zones.extend(batch_zones)
                            poll_event_generations.update(generations_before_read)
                    read_finished = clock.time()
                    lock_wait_ms = lock_wait_total_ms
                    read_ms = sum(batch_ms for _, _, batch_ms in batch_timings)
                    interval_display = (
                        round(interval_ms, 1) if interval_ms is not None else None
                    )
                    level = slow_read_log_level(read_ms)
                    in_startup_grace = (
                        _pir_slow_poll_log_level(clock.time() - poll_loop_started)
                        == logging.DEBUG
                    )
                    if level is not None and in_startup_grace:
                        # Keep slow-read history, but avoid startup-only warnings.
                        level = logging.DEBUG
                    if level is not None:
                        burst = self.pir_slow_reads.record(
                            read_ms,
                            interval_ms=interval_ms,
                            lock_wait_ms=lock_wait_ms,
                            resync_wait_ms=resync_wait_total_ms,
                            batches=batch_timings,
                            log_level=level,
                            startup_grace=in_startup_grace,
                        )
                        _LOGGER.log(
                            level,
                            "FlexC PIR poll slow: interval_ms=%s lock_wait_ms=%.1f "
                            "read_ms=%.1f resync_wait_ms=%.1f batches=%s",
                            interval_display,
                            lock_wait_ms,
                            read_ms,
                            resync_wait_total_ms,
                            batch_timings,
                        )
                        if burst is not None and not in_startup_grace:
                            _LOGGER.warning(
                                "FlexC PIR repeated slow reads: count=%d "
                                "window_seconds=60 max_read_ms=%.1f",
                                burst[0],
                                burst[1],
                            )
                        self.async_update_listeners()
                    elif (
                        lock_wait_ms >= 1000
                        or resync_wait_total_ms >= 1000
                        or (interval_ms is not None and interval_ms >= 2000)
                    ):
                        _LOGGER.debug(
                            "FlexC PIR poll delayed: interval_ms=%s "
                            "resync_wait_ms=%.1f lock_wait_ms=%.1f read_ms=%.1f",
                            interval_display,
                            resync_wait_total_ms,
                            lock_wait_ms,
                            read_ms,
                        )

                    changed = False
                    restored_area_ids: set[int] = set()
                    for raw_zone in raw_zones:
                        zone = _zone_state_from_status(raw_zone)
                        previous = self.state.zones.get(zone.zone_id)
                        if (
                            previous is not None
                            and previous.zone_type in (0, 1, 2, 30)
                            and self._pir_event_generation.get(zone.zone_id, 0)
                            != poll_event_generations.get(zone.zone_id, 0)
                        ):
                            # The response may predate a live EVENT received
                            # during this request. Keep the newer PIR state;
                            # a subsequent poll will reconcile it.
                            zone.logic_input = previous.logic_input
                        event_changed = _reconcile_zone_event_state(zone, previous)
                        # Temporary beta diagnostic: log motion-zone changes only.
                        # A nonzero actuation counter may reveal motion that
                        # returned to idle before the status read completed.
                        if zone.zone_type in (0, 1, 2, 30) and previous is not None:
                            input_changed = previous.logic_input != zone.logic_input
                            actuations_changed = (
                                previous.actuations_since_last_read
                                != zone.actuations_since_last_read
                            )
                            if input_changed or actuations_changed:
                                _LOGGER.debug(
                                    "FlexC PIR diagnostic: ZONE_ID=%s "
                                    "LOGIC_INPUT=%s->%s ACTUATIONS=%s->%s "
                                    "interval_ms=%s lock_wait_ms=%.1f read_ms=%.1f "
                                    "batches=%s",
                                    zone.zone_id,
                                    previous.logic_input,
                                    zone.logic_input,
                                    previous.actuations_since_last_read,
                                    zone.actuations_since_last_read,
                                    interval_display,
                                    lock_wait_ms,
                                    read_ms,
                                    batch_timings,
                                )
                        # Diagnostic only: track SPC zone status while an area
                        # retains an intrusion. Do not infer alarm clearance here.
                        area = (
                            self.state.areas.get(zone.area_id)
                            if zone.area_id is not None
                            else None
                        )
                        if (
                            _LOGGER.isEnabledFor(logging.DEBUG)
                            and area is not None
                            and area.alarm_event_active
                        ):
                            before_status = (
                                (
                                    previous.alarm_state,
                                    previous.proc_state,
                                    previous.restore_allowed,
                                )
                                if previous is not None
                                else None
                            )
                            after_status = (
                                zone.alarm_state,
                                zone.proc_state,
                                zone.restore_allowed,
                            )
                            if before_status != after_status:
                                _LOGGER.debug(
                                    "FlexC zone restore diagnostic: "
                                    "AREA_ID=%s ZONE_ID=%s "
                                    "before=%s after=%s",
                                    zone.area_id,
                                    zone.zone_id,
                                    before_status,
                                    after_status,
                                )
                        if (
                            event_changed
                            or previous is None
                            or (
                                previous.input_state != zone.input_state
                                or previous.logic_input != zone.logic_input
                                or previous.proc_state != zone.proc_state
                                or previous.status != zone.status
                                or previous.alarm_state != zone.alarm_state
                                or previous.inhibited != zone.inhibited
                                or previous.restore_allowed != zone.restore_allowed
                                or previous.actuations_since_last_read
                                != zone.actuations_since_last_read
                            )
                        ):
                            changed = True
                        # A restore event may arrive after polling already
                        # observed ALARM_STATE=0. Keep its pending confirmation
                        # until the next authoritative zone-status response.
                        if (
                            zone.area_id is not None
                            and (zone.area_id, zone.zone_id)
                            in self._pending_zone_restores
                        ):
                            restored_area_ids.add(zone.area_id)
                        self.state.zones[zone.zone_id] = zone
                    polled_zone_ids = {
                        _int_value(raw.get("ZONE_ID")) for raw in raw_zones
                    }
                    for area_id in restored_area_ids:
                        area = self.state.areas.get(area_id)
                        if (
                            area is None
                            or area.mode in (None, 0)
                            or not area.alarm_event_active
                        ):
                            continue
                        # Remove only individually confirmed restored zones;
                        # preserve the area alarm until the last one is cleared.
                        restored_zones = {
                            zone_id
                            for zone_id in area.triggered_alarm_zones
                            if (
                                (known_zone := self.state.zones.get(zone_id))
                                is not None
                                and known_zone.area_id == area_id
                                and known_zone.alarm_state == 0
                                and (area_id, zone_id) in self._pending_zone_restores
                                and zone_id in polled_zone_ids
                            )
                        }
                        if not restored_zones:
                            continue
                        area.triggered_alarm_zones.difference_update(restored_zones)
                        self._pending_zone_restores.difference_update(
                            {(area_id, zone_id) for zone_id in restored_zones}
                        )
                        # Active intrusion is cleared by FlexC return events, not
                        # by a restored alarm status alone.
                        _LOGGER.debug(
                            "FlexC confirmed zone alarm restoration: "
                            "AREA_ID=%s RESTORED=%s REMAINING=%s",
                            area_id,
                            tuple(sorted(restored_zones)),
                            tuple(sorted(area.triggered_alarm_zones)),
                        )
                        if (
                            not area.triggered_alarm_zones
                            and not area.active_alarm_zones
                        ):
                            area.alarm_event_active = False
                        changed = True
                    if changed:
                        publish_started = clock.time()
                        self.async_set_updated_data(self.state)
                        _LOGGER.debug(
                            "FlexC PIR publish diagnostic: processing_ms=%.1f "
                            "publish_call_ms=%.1f total_ms=%.1f",
                            (publish_started - read_finished) * 1000,
                            (clock.time() - publish_started) * 1000,
                            (clock.time() - poll_started) * 1000,
                        )
                except asyncio.CancelledError:
                    raise
                except (FlexCError, FlexMLError) as err:
                    _LOGGER.debug("SPC zone polling failed: %s", err)
                except Exception:
                    _LOGGER.exception(
                        "Unexpected error while polling SPC zones; polling will continue"
                    )
        except asyncio.CancelledError:
            if self._should_run_polling():
                _LOGGER.warning(
                    "SPC zone polling cancelled: entry_state=%s hass_state=%s discovery_requested=%s",
                    self.entry.state,
                    self.hass.state,
                    self._discovery_requested,
                )
            else:
                _LOGGER.debug(
                    "SPC zone polling cancelled: entry_state=%s hass_state=%s discovery_requested=%s",
                    self.entry.state,
                    self.hass.state,
                    self._discovery_requested,
                )
            raise
        finally:
            _LOGGER.debug("SPC zone polling stopped")
            current_task = asyncio.current_task()
            if self._zone_poll_task is current_task:
                self._zone_poll_task = None
                if self._should_run_polling():
                    _LOGGER.warning("SPC zone polling stopped unexpectedly; restarting")
                    self._schedule_zone_polling()

    def _schedule_xbus_polling(self) -> None:
        """Start periodic aggregate X-BUS reconciliation."""
        if not self._should_run_polling():
            return
        if not self._xbus_discovery_complete:
            return
        if self._xbus_poll_task is not None and not self._xbus_poll_task.done():
            return
        self._xbus_poll_task = self.entry.async_create_background_task(
            self.hass,
            self._async_xbus_poll_loop(),
            name=f"{DOMAIN} X-BUS polling",
            eager_start=False,
        )

    async def _async_xbus_poll_loop(self) -> None:
        """Periodically reconcile X-BUS inventory and raw status fields."""
        _LOGGER.debug("SPC X-BUS polling started")
        try:
            while True:
                await asyncio.sleep(
                    poll_delay_for_phase(XBUS_POLL_PHASE, XBUS_POLL_INTERVAL)
                )
                if not self._xbus_discovery_complete:
                    continue
                try:
                    async with self._client_operation_lock:
                        await self.client.async_ensure_connected()
                        raw_devices = await async_retry_read_once(
                            partial(async_get_xbus_status, self.client),
                            description="polling X-BUS devices",
                        )

                    changed = False
                    seen_serials: set[str] = set()
                    for raw_device in raw_devices:
                        serial = raw_device.get("SN")
                        if not serial:
                            _LOGGER.warning(
                                "Ignoring X-BUS ENETNODE without a serial number: %s",
                                raw_device,
                            )
                            continue
                        previous = self.state.xbus_devices.get(serial)
                        device = _xbus_device_state_from_status(raw_device, previous)
                        if device is None:
                            continue
                        seen_serials.add(serial)
                        if previous is None or previous.raw != device.raw:
                            changed = True
                        self.state.xbus_devices[serial] = device

                    missing_serials = set(self.state.xbus_devices) - seen_serials
                    if missing_serials:
                        changed = True
                        for serial in missing_serials:
                            del self.state.xbus_devices[serial]

                    if seen_serials != self._detected_xbus_serials:
                        self._detected_xbus_serials = seen_serials
                        changed = True

                    if changed:
                        self.async_set_updated_data(self.state)
                except asyncio.CancelledError:
                    raise
                except (FlexCError, FlexMLError) as err:
                    _LOGGER.debug("SPC X-BUS polling failed: %s", err)
                except Exception:
                    _LOGGER.exception(
                        "Unexpected error while polling SPC X-BUS; polling will continue"
                    )
        except asyncio.CancelledError:
            if self._should_run_polling():
                _LOGGER.warning(
                    "SPC X-BUS polling cancelled: entry_state=%s hass_state=%s discovery_requested=%s",
                    self.entry.state,
                    self.hass.state,
                    self._discovery_requested,
                )
            else:
                _LOGGER.debug(
                    "SPC X-BUS polling cancelled: entry_state=%s hass_state=%s discovery_requested=%s",
                    self.entry.state,
                    self.hass.state,
                    self._discovery_requested,
                )
            raise
        finally:
            _LOGGER.debug("SPC X-BUS polling stopped")
            current_task = asyncio.current_task()
            if self._xbus_poll_task is current_task:
                self._xbus_poll_task = None
                if self._should_run_polling():
                    _LOGGER.warning(
                        "SPC X-BUS polling stopped unexpectedly; restarting"
                    )
                    self._schedule_xbus_polling()

    async def async_shutdown(self) -> None:
        self._discovery_requested = False
        if self._activity_handle is not None:
            self._activity_handle.cancel()
            self._activity_handle = None
        activity_task = self._activity_task
        self._activity_task = None
        if activity_task is not None and not activity_task.done():
            activity_task.cancel()
            with suppress(asyncio.CancelledError):
                await activity_task
        zone_task = self._zone_poll_task
        self._zone_poll_task = None
        if zone_task is not None and not zone_task.done():
            zone_task.cancel()
            with suppress(asyncio.CancelledError):
                await zone_task
        xbus_task = self._xbus_poll_task
        self._xbus_poll_task = None
        if xbus_task is not None and not xbus_task.done():
            xbus_task.cancel()
            with suppress(asyncio.CancelledError):
                await xbus_task
        reconcile_task = self._reconnect_reconcile_task
        self._reconnect_reconcile_task = None
        if reconcile_task is not None and not reconcile_task.done():
            reconcile_task.cancel()
            with suppress(asyncio.CancelledError):
                await reconcile_task
        discovery_task = self._discovery_task
        self._discovery_task = None
        if discovery_task is not None and not discovery_task.done():
            discovery_task.cancel()
            with suppress(asyncio.CancelledError):
                await discovery_task
        await self.client.async_close()

    @staticmethod
    def _reconcile_area_intrusion(area: AreaState, previous: AreaState | None) -> None:
        """Preserve alarm events across polling; clear them on confirmed unset."""
        if area.mode == 0:
            return
        if previous is not None and previous.mode == area.mode:
            area.active_alarm_zones = set(previous.active_alarm_zones)
            area.triggered_alarm_zones = set(previous.triggered_alarm_zones)
            area.alarm_event_active = previous.alarm_event_active

    def _handle_flexc_event(self, event: dict[str, str]) -> None:
        # Diagnostic only: do not log raw EVENT attributes (may contain user data).
        def _number(key: str) -> int | None:
            try:
                return int(str(event.get(key)))
            except (TypeError, ValueError):
                return None

        event_id = _number("EV_ID")
        self._confirm_pin_from_event(event_id, _number("USER_ID"))
        area_id = _number("AREA_ID")
        zone_id = _number("ZONE_ID")
        if event_id is not None:
            # Identifiers only: never retain raw EVENT data or user details.
            self._last_event_identifiers = {
                "event_id": event_id,
                "area_id": area_id,
                "zone_id": zone_id,
                "received_at": datetime.now(UTC).isoformat(),
            }
            self._recent_event_identifiers = (
                getattr(self, "_recent_event_identifiers", [])
                + [self._last_event_identifiers]
            )[-20:]

        diagnostic_area = self.state.areas.get(area_id) if area_id is not None else None

        def _alarm_snapshot() -> (
            tuple[int | None, bool, tuple[int, ...], tuple[int, ...]] | None
        ):
            if diagnostic_area is None:
                return None
            return (
                diagnostic_area.mode,
                diagnostic_area.alarm_event_active,
                tuple(sorted(diagnostic_area.active_alarm_zones)),
                tuple(sorted(diagnostic_area.triggered_alarm_zones)),
            )

        before = _alarm_snapshot() if _LOGGER.isEnabledFor(logging.DEBUG) else None
        fault_changed = apply_event(self.state.faults, event)
        if fault_changed and str(event.get("EV_ID")) in ("5206", "5207"):
            panel_tamper = self.state.faults.panel_tamper
            if panel_tamper is not None:
                self._tamper_store.async_delay_save(
                    lambda: {"panel_tamper": panel_tamper}, 1
                )
        if event_id in PANEL_ALERT_EVENT_IDS:
            self._schedule_panel_status_refresh()
        panel_changed = apply_panel_event(self.state.panel, event)
        history_changed = SpcFlexCCoordinator._apply_area_history_event(self, event)
        # Ignore duplicate/out-of-order mode events; preserve the current mode.
        is_mode_event = event_id in (3501, 3502, 3503, 3504)
        # Events without timestamps still carry valid live state transitions.
        # Only reject a mode event when its timestamp is provably stale.
        event_time = (
            _spc_datetime(event.get("TIMESTAMP"), dt_util.get_default_time_zone())
            if is_mode_event
            else None
        )
        area_history = (
            self._area_history.get(area_id, {}) if area_id is not None else {}
        )
        latest_time = max(
            (
                value
                for key in ("last_arm_time", "last_disarm_time")
                if isinstance((value := area_history.get(key)), datetime)
            ),
            default=None,
        )
        stale_mode_event = (
            is_mode_event
            and event_time is not None
            and latest_time is not None
            and event_time < latest_time
        )
        area_changed = (
            False if stale_mode_event else apply_area_event(self.state.areas, event)
        )
        intrusion_changed = apply_area_intrusion_event(self.state.areas, event)
        if event_id in (1100, 1101) and area_id is not None and zone_id is not None:
            area = self.state.areas.get(area_id)
            if (
                area is not None
                and area.mode in (1, 2, 3)
                and zone_id in area.triggered_alarm_zones
            ):
                self._pending_zone_restores.add((area_id, zone_id))
                if zone_id in area.active_alarm_zones:
                    area.active_alarm_zones.discard(zone_id)
                    intrusion_changed = True
        elif event_id in (1000, 1001) and area_id is not None and zone_id is not None:
            self._pending_zone_restores.discard((area_id, zone_id))
        elif event_id == 3501 and area_id is not None:
            self._pending_zone_restores = {
                key for key in self._pending_zone_restores if key[0] != area_id
            }
        if str(event.get("EV_ID")) == "3501":
            try:
                area_id = int(str(event.get("AREA_ID")))
            except (TypeError, ValueError):
                area_id = None
            area = self.state.areas.get(area_id) if area_id is not None else None
            if area is not None and area.mode == 0:
                if (
                    area.alarm_event_active
                    or area.active_alarm_zones
                    or area.triggered_alarm_zones
                ):
                    intrusion_changed = True
                area.active_alarm_zones.clear()
                area.triggered_alarm_zones.clear()
                area.alarm_event_active = False
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(
                "FlexC alarm diagnostic: EV_ID=%s AREA_ID=%s ZONE_ID=%s "
                "before=%s after=%s",
                event_id,
                area_id,
                zone_id,
                before,
                _alarm_snapshot(),
            )
        zone_changed = apply_zone_event(self.state.zones, event)
        if event_id in (2100, 2101) and zone_id is not None:
            zone = self.state.zones.get(zone_id)
            if (
                zone is not None
                and zone.zone_type in (0, 1, 2, 30)
                and (area_id is None or zone.area_id == area_id)
            ):
                new_logic_input = 1 if event_id == 2100 else 0
                self._pir_event_generation[zone_id] = (
                    self._pir_event_generation.get(zone_id, 0) + 1
                )
                zone_changed = zone.logic_input != new_logic_input or zone_changed
                zone.logic_input = new_logic_input
                zone.updated_at = datetime.now(UTC)
                _LOGGER.debug(
                    "FlexC zone EVENT state: EV_ID=%s ZONE_ID=%s active=%s",
                    event_id,
                    zone_id,
                    bool(new_logic_input),
                )
        xbus_changed = apply_xbus_event(self.state.xbus_devices, event)
        if (
            fault_changed
            or panel_changed
            or area_changed
            or history_changed
            or intrusion_changed
            or zone_changed
            or xbus_changed
            or event_id is not None
        ):
            self.async_set_updated_data(self.state)
