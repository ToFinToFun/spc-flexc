"""Constants for the SPC FlexC integration."""

from homeassistant.const import Platform

# Integration
DOMAIN = "spc_flexc"

PLATFORMS = (
    Platform.ALARM_CONTROL_PANEL,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CALENDAR,
    Platform.LOCK,
    Platform.SENSOR,
    Platform.SWITCH,
)

# Configuration
DEFAULT_PORT = 52000
DEFAULT_PANEL_INTERVAL = 60.0

CONF_PORT = "port"
CONF_KEY = "encryption_key"
CONF_COMMAND_USERNAME = "command_username"
CONF_COMMAND_PASSWORD = "command_password"
CONF_USER_ALIASES = "user_aliases"
# Options: door ID (str) -> serial number of the door controller it is on.
CONF_DOOR_CONTROLLERS = "door_controllers"
# Options: show the SPC app as a page in the sidebar (default on).
CONF_SIDEBAR_PANEL = "show_in_sidebar"
# Options: keep the panel clock right (default on). A panel that keeps time
# from the mains can drift up to about a minute. Checked with every panel
# read; when it is more than CLOCK_SYNC_LIMIT seconds off, SET_CLOCK sets it
# to Home Assistant's time, at most once per CLOCK_SYNC_INTERVAL seconds.
# Each set adds "Datum och tid justerat" to the panel's system log.
CONF_CLOCK_SYNC = "keep_clock_right"
CLOCK_SYNC_LIMIT = 3  # above the 1-2 s measurement noise
CLOCK_SYNC_INTERVAL = 3600
# Options: zone IDs on the wireless receiver (default: every zone that is on
# no wired hardware while a receiver answers).
CONF_WIRELESS_ZONES = "wireless_zones"
# Options: zone ID (str) -> radio ID of the wireless detector on it, as the
# web page Status > Hardware > Wireless status lists it (FlexC does not).
CONF_WIRELESS_RADIO_IDS = "wireless_radio_ids"
# Optional SPC engineer (Programtekniker) login, entered in the SPC app.
# Remembered in the config entry only when the owner chooses to; otherwise
# kept in memory and ended after ENGINEER_IDLE_LOGOUT seconds unused.
ENGINEER_IDLE_LOGOUT = 1800
CONF_ENGINEER_USERNAME = "engineer_username"
CONF_ENGINEER_PASSWORD = "engineer_password"

# Live polling
ZONE_POLL_INTERVAL = 1.0
ZONE_POLL_PHASE = 0.0
ZONE_POLL_BATCH_SIZE = 16

DOOR_POLL_INTERVAL = 1.0
DOOR_POLL_PHASE = 1.0 / 3.0

MG_POLL_INTERVAL = 1.0
MG_POLL_PHASE = 2.0 / 3.0

# X-BUS status is aggregate and FlexC events provide immediate fault changes.
# Poll periodically as a reconciliation path for missed events and state drift.
XBUS_POLL_INTERVAL = 30.0
XBUS_POLL_PHASE = 5.0

# Validated on a real X-BUS keypad with an active tamper fault.
# Bit 0x0002 identifies the physical tamper input and its inhibit/isolate state.
XBUS_TAMPER_INPUT_MASK = 0x0002
XBUS_TAMPER_INHIBIT_MASK = 0x0002
XBUS_TAMPER_ISOLATE_MASK = 0x0002
# Bits of the X-BUS INPUT/ALERT/INHIBIT/ISOLATE masks whose meaning is known.
# 0x0008 = mains fault: the owner's web page listed "IO Garage X-BUS expander
# nätspänningsfel - ISOLERAD" while ISOLATE was 000A (2026-11-11).
XBUS_MASK_BITS: dict[int, str] = {0x0002: "tamper", 0x0008: "mains_fault"}

# FlexC ATS
ATS_IDS = range(1, 5)

# Discovery is protocol-driven: valid-but-unused IDs may return RESULT=0 with
# an empty reply, while the first out-of-range IDs return RESULT=102. The
# generous safety caps below prevent an endless scan if a panel never reports
# that boundary.
DISCOVERY_BATCH_SIZE = 8
AREA_DISCOVERY_MAX_ID = 64
ZONE_DISCOVERY_MAX_ID = 512
DOOR_DISCOVERY_MAX_ID = 128

# SPC zone types
SPC_ZONE_TYPES: dict[int, str] = {
    0: "alarm",
    1: "entry_exit",
    2: "exit_terminator",
    3: "fire",
    4: "emergency_exit",
    5: "line",
    6: "panic",
    7: "hold_up",
    8: "tamper",
    9: "technical",
    10: "medical",
    11: "keyswitch",
    13: "shunt",
    14: "x_shunt",
    15: "detector_fault",
    16: "locking_supervision",
    18: "all_well",
    19: "hold_up_fault",
    20: "warning_fault",
    21: "set_unset_authorization",
    22: "locking_element",
    23: "glass_break",
    24: "water",
    25: "heat",
    26: "fridge_freezer",
    27: "gas",
    28: "sprinkler",
    29: "co2",
    30: "entry_exit_2",
}
