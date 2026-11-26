"""READ_INTRUDER_CFG: the panel's system options and timers (read-only).

All attributes of the INTRUDER element are returned, keys in lower case.
They are settings (for example the number of PIN digits, code lockout,
whether duress is enabled, bell and delay times), not codes. Times are as the
panel sends them (mostly seconds).
"""

from __future__ import annotations

from .flexml import (
    FlexMLError,
    _build_command_envelope,
    _parse_reply_root,
    _validate_reply,
)


def build_intruder_config_command(username: str, password: str) -> str:
    """Build CMD_READ_INTRUDER_CFG."""
    return _build_command_envelope("<CMD_READ_INTRUDER_CFG />", username, password)


def parse_intruder_config(response: str) -> dict[str, str]:
    """Return all INTRUDER attributes, keys lower-case."""
    root = _parse_reply_root(response)
    reply = root.find("REPLY_READ_INTRUDER_CFG")
    if reply is None:
        raise FlexMLError("REPLY_READ_INTRUDER_CFG not found")
    _validate_reply(reply, "REPLY_READ_INTRUDER_CFG")
    element = reply.find("INTRUDER")
    if element is None:
        raise FlexMLError("INTRUDER not found")
    return {key.lower(): value for key, value in element.attrib.items()}


# Mapped 2026-11-13 against the web page (Konfiguration > System): one option
# at a time ticked on the web page and read back over FlexC, then set back.
# Keys are the web page's field names.

# Systemalternativ check boxes: (FlexC field, bit).
SYSTEM_OPTION_BITS: dict[str, tuple[str, int]] = {
    "retrigger": ("MODE", 0x00000008),
    "bellonfirst": ("MODE", 0x00000010),
    "open_zones": ("MODE", 0x00000040),
    "autorestore": ("MODE", 0x00000200),
    "bellfts": ("MODE", 0x00002000),
    "strobefts": ("MODE", 0x00004000),
    "coded_restore": ("MODE", 0x00040000),
    "always_state": ("MODE", 0x00080000),
    "callcs_enable": ("MODE", 0x00200000),
    "keyfob_restore": ("MODE", 0x00400000),
    "restore_on_unset": ("MODE", 0x01000000),
    "offline_tamper": ("MODE", 0x02000000),
    "engineer_restore": ("MODE", 0x04000000),
    "alarmexit": ("MODE", 0x10000000),
    "suspicion_audible": ("MODE", 0x40000000),
    "offline_cameras": ("MODE", 0x80000000),
    "alert_forbid_set": ("MODE_EXT", 0x00000001),
    "seismic_test_on_set": ("MODE_EXT", 0x00000002),
    "duress_retrigger": ("MODE_EXT", 0x00000004),
    "panic_retrigger": ("MODE_EXT", 0x00000008),
    "aex_no_led": ("MODE_EXT", 0x00000010),
    "eng_allow_exit": ("MODE_EXT", 0x00000020),
    "silence_audio_ver": ("MODE_EXT", 0x00000040),
    "reader_leds": ("MODE_EXT", 0x00000080),
    "report_full_engineer": ("MODE_EXT", 0x00000100),
    "alarm_on_ftc": ("MODE_EXT", 0x00000200),
    "alarm_entry": ("MODE_EXT", 0x00000400),
    "hide_bypass_message": ("MODE_EXT", 0x00000800),
    "log_keypad_access": ("MODE_EXT", 0x00002000),
    "final_exit": ("MODE_EXT", 0x00008000),
}
# Systemalternativ check boxes with a FlexC field of their own.
SYSTEM_OPTION_FIELDS: dict[str, str] = {"outputs_full_engineer": "OUTPUTS_FULL_ENG"}

# Systemalternativ and Standard choices: web field -> FlexC field (same value).
SYSTEM_CHOICES: dict[str, str] = {
    "continent": "CONTINENT",
    "region": "REGION",
    "type": "TYPE",
    "grade": "GRADE",
    "watchdog_output_mode": "WATCHDOG_OUTPUT_MODE",
    "antimaskset": "ANTIMASK_SET",
    "antimaskunset": "ANTIMASK_UNSET",
    "outofboundset": "OUT_OF_BOUNDS_MODE_SET",
    "outofboundunset": "OUT_OF_BOUNDS_MODE_UNSET",
    "zoneunstableset": "UNSTABLE_MODE_SET",
    "zoneunstableunset": "UNSTABLE_MODE_UNSET",
    "eol": "EOL",
    "zonenobells": "ZONE_NO_BELL_ATTR",
    "duress": "DURESS",
    "doormode_set": "DOOR_MODE_SET",
    "doormode_unset": "DOOR_MODE_UNSET",
    "pindigits": "PIN",
    "parta_name": "NAMEA",
    "partb_name": "NAMEB",
}

# Timers: web field -> (FlexC field, the web page's unit, FlexC units per web
# unit). The bell and confirmation times are minutes on the web page but
# seconds in FlexC (15 min = 900); every other value is the same number.
SYSTEM_TIMERS: dict[str, tuple[str, str, int]] = {
    "intbell": ("INTBELLTIME", "min", 60),
    "extbell": ("EXTBELLTIME", "min", 60),
    "extbelldelay": ("EXTBELLDELAY", "s", 1),
    "chime": ("CHIMETIME", "s", 1),
    "confirm": ("CONFIRMTIME", "min", 60),
    "confirm_holdup": ("HOLDUP_CONFIRM", "min", 1),
    "dialer": ("DIALERDELAY", "s", 1),
    "dialerpartset": ("DIALERDELAYPARTSET", "s", 1),
    "alarm_abort": ("ALARM_ABORT_TIME", "s", 1),
    "setting_auth": ("SETTING_AUTH_TIME", "s", 1),
    "finalexit": ("FINALEXITTIME", "s", 1),
    "fullsetbell": ("FULLSETBELLTIME", "s", 1),
    "failtoset": ("FTSTIME", "s", 1),
    "fullsetstrobe": ("FULLSETSTROBETIME", "s", 1),
    "delayed_unset_buzzer": ("DELAYED_UNSET_BUZZER_TIME", "s", 1),
    "doubleknock": ("DKTIME", "s", 1),
    "soak": ("SOAK", "d", 1),
    "seismic_autotest": ("SEISMIC_AUTOTEST_TIME", "h", 1),
    "seismic_test_duration": ("SEISMIC_TEST_DURATION", "s", 1),
    "auto_restore_delay": ("AUTO_RESTORE_DELAY", "s", 1),
    "alarm_lockout_test_duration": ("ALARM_LOCKOUT_TIME", "min", 1),
    "extbellstrobe": ("EXTBELLSTROBETIME", "min", 60),
    "mains": ("MAINSDELAY", "min", 1),
    "rf_jam_delay": ("RF_JAM_DELAY", "s", 1),
    "engtime": ("ENGTIME", "min", 1),
    "engautologout": ("ENGINEER_AUTO_OUT", "min", 1),
    "rkd": ("RKDTIMEOUT", "s", 1),
    "rkd_language": ("KEYPAD_LANGUAGE_TIMEOUT", "s", 1),
    "fire_prealarm": ("FIRE_PREALARM_TIME", "s", 1),
    "fire_recognition": ("FIRE_RECOGNITION_TIME", "s", 1),
    "user_pin_validity_peroid": ("USER_VALID_PIN_TIME", "d", 1),
    "user_pin_changes_limit": ("USER_VALID_PIN_CHANGES", "", 1),
    "user_pin_change_warning_time": ("USER_WARN_PIN", "d", 1),
    "user_pin_code_lockout": ("CODE_LOCKOUT1", "", 1),
    "user_pin_code_lockout2": ("CODE_LOCKOUT2", "", 1),
    "user_pin_code_lockout_time": ("CODE_LOCKOUT_TIME", "s", 1),
    "rfoutputtime": ("RFOUTPUT_TIME", "s", 1),
    "timesynctime": ("TIME_SYNC_LIMIT", "s", 1),
    "net_timeout": ("NET_FAIL_TIME", "s", 1),
    "video_timeout": ("CAMERA_OFFLINE", "s", 1),
    "frequent": ("FREQUENTTIME", "h", 1),
    "duress_reset_time": ("DURESS_RESET_TIME", "min", 1),
    "holdup_reset_time": ("HOLDUP_RESET_TIME", "min", 1),
}


def decode_system_settings(config: dict[str, str]) -> dict[str, object]:
    """The panel's settings by the web page's names, timers in its units.

    ``config`` is parse_intruder_config's dict (lower-case keys). Values that
    the panel did not send are left out.
    """
    raw = {key.upper(): value for key, value in config.items()}

    def number(field: str) -> int | None:
        try:
            return int(raw[field])
        except (KeyError, ValueError):
            return None

    options: dict[str, bool] = {}
    for name, (field, bit) in SYSTEM_OPTION_BITS.items():
        if field in raw:
            try:
                options[name] = bool(int(raw[field], 16) & bit)
            except ValueError:
                continue
    for name, field in SYSTEM_OPTION_FIELDS.items():
        if field in raw:
            options[name] = raw[field] == "1"
    # PIN is the number of PIN digits (4-8), not a code.
    choices = {
        name: raw[field] for name, field in SYSTEM_CHOICES.items() if field in raw
    }
    timers: dict[str, dict[str, object]] = {}
    for name, (field, unit, per_unit) in SYSTEM_TIMERS.items():
        value = number(field)
        if value is not None:
            shown = value / per_unit
            timers[name] = {
                "value": int(shown) if shown == int(shown) else shown,
                "unit": unit,
            }
    return {"options": options, "choices": choices, "timers": timers}
