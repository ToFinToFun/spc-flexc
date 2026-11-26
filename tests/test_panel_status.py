"""CMD_STATUS_PANEL: system alert masks, Ethernet, entities and the ATS network log."""

from datetime import UTC
from unittest.mock import MagicMock

import pytest

from custom_components.spc_flexc.binary_sensor import (
    SpcEthernetSensor,
    SpcSystemAlertSensor,
)
from custom_components.spc_flexc.flexc.flexml import FlexMLError
from custom_components.spc_flexc.flexc.logs import build_log_command, parse_log
from custom_components.spc_flexc.flexc.panel_status import (
    SYSTEM_ALERTS,
    build_status_panel_command,
    parse_status_panel,
)
from custom_components.spc_flexc.models import SpcState

# Masks captured on an SPC4300 while Network Fault was isolated and Code
# Tamper inhibited; Ethernet values are placeholders.
STATUS = (
    '<FLEXML_REPLY VER="1.0"><REPLY_STATUS_PANEL RESULT="0" CMD_RESULT="OK">'
    '<SYSINFO TIME="00114510112026" ENGMODE="0" />'
    '<SYSALERT INPUT="00000001" ALERT="00000000" INHIBIT="00400000" ISOLATE="01000000" '
    'INHIBIT_ALLOWED_1="1" ISOLATE_ALLOWED_1="1" INHIBIT_ALLOWED_4194304="1" '
    'ISOLATE_ALLOWED_4194304="0" />'
    '<ETHERNETINFO FITTED="1" STATE="1" DHCP_ENABLED="1" IP_ADDRESS="192.0.2.10" '
    'NETMASK="255.255.255.0" GATEWAY="192.0.2.1" />'
    "</REPLY_STATUS_PANEL></FLEXML_REPLY>"
)


def test_build_status_panel_command() -> None:
    assert "<CMD_STATUS_PANEL />" in build_status_panel_command("u", "p")


def test_parse_status_panel_alerts_and_ethernet() -> None:
    status = parse_status_panel(STATUS)
    assert len(status.alerts) == len(SYSTEM_ALERTS)
    mains = status.alerts["mains_fault"]
    assert (mains.active, mains.inhibited, mains.isolated) == (True, False, False)
    assert mains.inhibit_allowed is True
    code = status.alerts["code_tamper"]
    assert code.inhibited and not code.isolated
    assert code.isolate_allowed is False
    network = status.alerts["network_fault"]
    assert network.isolated and not network.active
    assert network.inhibit_allowed is None
    assert status.ethernet["STATE"] == "1"


def test_parse_status_panel_without_masks_or_errors() -> None:
    empty = parse_status_panel(
        '<FLEXML_REPLY VER="1.0"><REPLY_STATUS_PANEL RESULT="0" CMD_RESULT="OK">'
        '<SYSALERT INPUT="zz" /></REPLY_STATUS_PANEL></FLEXML_REPLY>'
    )
    assert empty.alerts == {} and empty.ethernet == {}
    with pytest.raises(FlexMLError):
        parse_status_panel('<FLEXML_REPLY VER="1.0"></FLEXML_REPLY>')


def test_system_alert_bits_are_unique() -> None:
    assert len({alert.bit for alert in SYSTEM_ALERTS}) == len(SYSTEM_ALERTS)
    assert len({alert.key for alert in SYSTEM_ALERTS}) == len(SYSTEM_ALERTS)


def _coordinator() -> MagicMock:
    coordinator = MagicMock()
    coordinator.entry.entry_id = "test"
    coordinator.data = SpcState()
    return coordinator


def test_system_alert_sensor() -> None:
    coordinator = _coordinator()
    sensor = SpcSystemAlertSensor(coordinator, "network_fault", 38)
    assert sensor.unique_id == "test_system_alert_network_fault"
    assert sensor.available is False
    coordinator.data.system_alerts = parse_status_panel(STATUS).alerts
    assert sensor.is_on is False
    assert sensor.extra_state_attributes["isolated"] is True
    assert SpcSystemAlertSensor(coordinator, "mains_fault", 0).is_on is True


def test_ethernet_sensor() -> None:
    coordinator = _coordinator()
    sensor = SpcEthernetSensor(coordinator)
    assert sensor.available is False
    coordinator.data.ethernet = parse_status_panel(STATUS).ethernet
    assert sensor.is_on is True
    assert sensor.extra_state_attributes["dhcp"] is True


def test_ats_network_log() -> None:
    assert '<CMD_GET_FLEXC_ATS_NETWORK_LOG ATS_ID="2" />' in build_log_command(
        "ats_network", 2, "u", "p"
    )
    records = parse_log(
        '<FLEXML_REPLY VER="1.0"><REPLY_GET_FLEXC_ATS_NETWORK_LOG RESULT="0" CMD_RESULT="OK">'
        '<ATS_NETWORK_LOG ATS_ID="2" MSG_ID="4" TIMESTAMP="22114709112026" '
        'NETWORK_LOG_MESSAGE="Poll" />'
        "</REPLY_GET_FLEXC_ATS_NETWORK_LOG></FLEXML_REPLY>",
        "ats_network",
        UTC,
    )
    assert records == [
        {
            "time": "2026-11-09T22:11:47+00:00",
            "ats_id": 2,
            "message_id": 4,
            "text": "Poll",
        }
    ]


def test_atp_logs() -> None:
    assert '<CMD_GET_FLEXC_ATP_LOG ATS_ID="2" ATP_SEQ_ID="1" />' in build_log_command(
        "atp", 2, "u", "p"
    )
    assert 'ATP_SEQ_ID="3"' in build_log_command("atp_network", 2, "u", "p", 3)
    records = parse_log(
        '<FLEXML_REPLY VER="1.0"><REPLY_GET_FLEXC_ATP_LOG RESULT="0" CMD_RESULT="OK">'
        '<ATP_LOG ATS_ID="2" ATP_SEQ_ID="1" MSG_ID="43" DATA="0" TIMESTAMP="00375110112026" '
        'ATP_LOG_MESSAGE="RX ok" /></REPLY_GET_FLEXC_ATP_LOG></FLEXML_REPLY>',
        "atp",
        UTC,
    )
    assert records[0]["message_id"] == 43 and records[0]["atp"] == 1


def test_intruder_config_returns_all_settings() -> None:
    from custom_components.spc_flexc.flexc.intruder_config import (
        build_intruder_config_command,
        parse_intruder_config,
    )

    assert "<CMD_READ_INTRUDER_CFG />" in build_intruder_config_command("u", "p")
    config = parse_intruder_config(
        '<FLEXML_REPLY VER="1.0"><REPLY_READ_INTRUDER_CFG RESULT="0" CMD_RESULT="OK">'
        '<INTRUDER GRADE="0" REGION="6" PIN="4" DURESS="1" NAMEA="Night" '
        'INTBELLTIME="900" /></REPLY_READ_INTRUDER_CFG></FLEXML_REPLY>'
    )
    assert config == {
        "grade": "0",
        "region": "6",
        "pin": "4",
        "duress": "1",
        "namea": "Night",
        "intbelltime": "900",
    }
