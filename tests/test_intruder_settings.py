"""READ_INTRUDER_CFG decoded by the web page's names (mapped 2026-11-13)."""

from custom_components.spc_flexc.flexc.intruder_config import decode_system_settings


def test_reference_panel_settings() -> None:
    config = {
        "mode": "00120252",
        "mode_ext": "00000000",
        "outputs_full_eng": "0",
        "region": "6",
        "type": "2",
        "pin": "4",
        "namea": "Nattläge",
        "intbelltime": "900",
        "confirmtime": "1800",
        "holdup_confirm": "480",
        "code_lockout_time": "900",
        "frequenttime": "336",
    }
    settings = decode_system_settings(config)
    options = settings["options"]
    assert options["bellonfirst"] and options["open_zones"] and options["autorestore"]
    assert not options["retrigger"] and not options["alarm_entry"]
    assert not options["outputs_full_engineer"]
    assert settings["choices"]["region"] == "6"
    assert settings["choices"]["pindigits"] == "4"
    assert settings["choices"]["parta_name"] == "Nattläge"
    timers = settings["timers"]
    assert timers["intbell"] == {"value": 15, "unit": "min"}
    assert timers["confirm"] == {"value": 30, "unit": "min"}
    assert timers["confirm_holdup"] == {"value": 480, "unit": "min"}
    assert timers["user_pin_code_lockout_time"] == {"value": 900, "unit": "s"}
    assert timers["frequent"] == {"value": 336, "unit": "h"}
