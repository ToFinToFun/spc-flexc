"""User profiles, user status and unknown cards."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.spc_flexc.coordinator import SpcFlexCCoordinator
from custom_components.spc_flexc.flexc.flexml import FlexMLError
from custom_components.spc_flexc.flexc.profiles import (
    apply_profile_changes,
    areas_from_mask,
    build_add_user_profile_command,
    build_delete_user_profile_command,
    build_edit_user_profile_command,
    build_user_profile_config_command,
    mask_from_areas,
    parse_user_profile_records,
    user_profile,
)
from custom_components.spc_flexc.flexc.users import (
    build_unknown_cards_command,
    build_user_status_command,
    parse_unknown_cards,
    parse_user_status,
)
from custom_components.spc_flexc.models import SpcState
from custom_components.spc_flexc.sensor import SpcUserProfilesSensor

# Shape of a real SPC4300 (3.14.1) reply; names are placeholders.
PROFILES_REPLY = (
    '<FLEXML_REPLY VER="1.0"><REPLY_GET_USER_PROFILE_CONFIG RESULT="0" CMD_RESULT="OK">'
    '<USER_PROFILE_CONFIG USER_PROFILE_ID="1" GID="0" NAME="Standard Anv&#228;ndare" '
    'AREAS="0000000000000007" USER_RIGHTS="006F443F" USER_RIGHTS2="00000000" '
    'CALENDAR="0" SITE_CODE="0" DOOR1="0" DOOR2="0" DOOR3="0" />'
    '<USER_PROFILE_CONFIG USER_PROFILE_ID="3" GID="0" NAME="Child" '
    'AREAS="0000000000000003" USER_RIGHTS="00000000" USER_RIGHTS2="00000000" '
    'CALENDAR="2" SITE_CODE="0" DOOR1="2" DOOR3="2" />'
    "</REPLY_GET_USER_PROFILE_CONFIG></FLEXML_REPLY>"
)
OK = '<FLEXML_REPLY VER="1.0"><REPLY_{0} RESULT="0" CMD_RESULT="OK"/></FLEXML_REPLY>'


def test_profile_read_command_and_parse() -> None:
    assert '<CMD_GET_USER_PROFILE_CONFIG USER_PROFILE_ID="0" />' in (
        build_user_profile_config_command(0, "u", "p")
    )
    profiles = [user_profile(r) for r in parse_user_profile_records(PROFILES_REPLY)]
    assert profiles[0].name == "Standard Användare"
    assert profiles[0].areas == (1, 2, 3)
    assert profiles[0].doors == {1: "0", 2: "0", 3: "0"}
    assert profiles[1].areas == (1, 2)
    assert profiles[1].calendar == 2
    assert profiles[1].doors == {1: "2", 3: "2"}


def test_profile_read_error_is_raised() -> None:
    with pytest.raises(FlexMLError):
        parse_user_profile_records(
            '<FLEXML_REPLY VER="1.0"><REPLY_GET_USER_PROFILE_CONFIG RESULT="102" '
            'CMD_RESULT="ERROR"/></FLEXML_REPLY>'
        )


def test_area_mask_round_trip() -> None:
    assert areas_from_mask("000000000000000F") == (1, 2, 3, 4)
    assert mask_from_areas([1, 4]) == "0000000000000009"
    assert mask_from_areas([]) == "0000000000000000"
    with pytest.raises(ValueError):
        mask_from_areas([65])


def test_edit_profile_keeps_other_fields() -> None:
    record = parse_user_profile_records(PROFILES_REPLY)[1]
    updated = apply_profile_changes(
        record, name="Guest", areas=[3], calendar=0, doors={2: "0", 1: None}
    )
    command = build_edit_user_profile_command(updated, "u", "p")
    assert '<CMD_EDIT_USER_PROFILE USER_PROFILE_ID="3"' in command
    assert 'NAME="Guest"' in command and 'AREAS="0000000000000004"' in command
    assert 'CALENDAR="0"' in command and 'DOOR2="0"' in command
    assert "DOOR1=" not in command and 'DOOR3="2"' in command
    assert 'USER_RIGHTS="00000000"' in command
    assert record["NAME"] == "Child"
    with pytest.raises(ValueError):
        apply_profile_changes(record, name="x" * 17)


def test_add_and_delete_profile_commands() -> None:
    add = build_add_user_profile_command(7, "Flat", [4], 0, "u", "p")
    assert '<CMD_ADD_USER_PROFILE USER_PROFILE_ID="7"' in add
    assert 'NAME="Flat"' in add and 'AREAS="0000000000000008"' in add
    assert '<CMD_DELETE_USER_PROFILE USER_PROFILE_ID="7" />' in (
        build_delete_user_profile_command(7, "u", "p")
    )


def test_user_status_parse() -> None:
    assert '<CMD_GET_USER_STATUS USER_ID="99" />' in build_user_status_command(
        99, "u", "p"
    )
    # Real reply shape (test user 99, 2026-11-10), including the stray spaces.
    status = parse_user_status(
        '<FLEXML_REPLY VER="1.0"><REPLY_GET_USER_STATUS RESULT="0" CMD_RESULT="OK">'
        '<GET_USER_STATUS GROUP_SIDE_MASK ="0" GROUP_SIDE_VALID_MASK ="0" '
        'INVALID_PIN_COUNT ="2" USER_ALERTS_STATE="0" USER_ALERTS_STATUS="0" '
        'USER_ALERTS_ACCEPTED ="0" FOB_LOW_BATTERY_COUNT="0" '
        'FOB_LOW_DATE_FIRST ="00000001012000" LAST_PIN_CHANGE="10021510112026" '
        'PIN_CHANGE_COUNT="3" /></REPLY_GET_USER_STATUS></FLEXML_REPLY>'
    )
    assert status["invalid_pin_count"] == 2
    assert status["pin_change_count"] == 3
    assert status["last_pin_change"] == "2026-11-10T10:02:15"
    assert status["fob_low_date_first"] is None
    assert status["user_alerts_state"] == "0"


def test_unknown_cards_show_the_card_but_mask_codes() -> None:
    assert "<CMD_GET_UNKNOWN_CARDS />" in build_unknown_cards_command("u", "p")
    cards = parse_unknown_cards(
        '<FLEXML_REPLY VER="1.0"><REPLY_GET_UNKNOWN_CARDS RESULT="0" CMD_RESULT="OK">'
        '<UNKNOWN_CARD CARD_NO="00012345" DOOR_ID="3" TIMESTAMP="10021510112026" '
        'USER_CODE="1234" />'
        "</REPLY_GET_UNKNOWN_CARDS></FLEXML_REPLY>"
    )
    assert cards == [
        {
            "card_no": "00012345",
            "door_id": "3",
            "timestamp": "10021510112026",
            "user_code": "***",
            "index": "1",
        }
    ]


def _coordinator() -> MagicMock:
    coordinator = MagicMock(spec=SpcFlexCCoordinator)
    coordinator._client_operation_lock = asyncio.Lock()
    coordinator.client = MagicMock()
    coordinator.client.command_username = "u"
    coordinator.client.command_password = "p"
    coordinator.client.async_ensure_connected = AsyncMock()
    coordinator.state = SpcState()
    coordinator._async_read_user_profiles_locked = AsyncMock()
    return coordinator


@pytest.mark.asyncio
async def test_edit_profile_reads_record_then_sends_once() -> None:
    coordinator = _coordinator()
    coordinator._async_read_user_profile_record_locked = AsyncMock(
        return_value=parse_user_profile_records(PROFILES_REPLY)[0]
    )
    coordinator.client.async_send_flexml = AsyncMock(
        return_value=OK.format("EDIT_USER_PROFILE")
    )
    await SpcFlexCCoordinator.async_edit_user_profile(coordinator, 1, areas=[1])
    coordinator._async_read_user_profile_record_locked.assert_awaited_once_with(1)
    coordinator.client.async_send_flexml.assert_awaited_once()
    sent = coordinator.client.async_send_flexml.call_args.args[0]
    assert 'AREAS="0000000000000001"' in sent and 'NAME="Standard' in sent
    coordinator._async_read_user_profiles_locked.assert_awaited_once_with(force=True)


@pytest.mark.asyncio
async def test_read_profiles_skips_when_nothing_changed() -> None:
    coordinator = _coordinator()
    del coordinator._async_read_user_profiles_locked
    coordinator._user_profiles_unsupported = False
    coordinator.client.async_send_flexml = AsyncMock(return_value=PROFILES_REPLY)
    await SpcFlexCCoordinator._async_read_user_profiles_locked(coordinator)
    assert set(coordinator.state.user_profiles) == {1, 3}
    # Change times unknown (None): the profiles are read again next time.
    await SpcFlexCCoordinator._async_read_user_profiles_locked(coordinator)
    assert coordinator.client.async_send_flexml.await_count == 2


def test_profiles_sensor() -> None:
    coordinator = MagicMock()
    coordinator.entry.entry_id = "test"
    coordinator.entry.data = {"host": "192.0.2.1"}
    profiles = {
        p.profile_id: p
        for p in map(user_profile, parse_user_profile_records(PROFILES_REPLY))
    }
    coordinator.data = SpcState(user_profiles=profiles)
    sensor = SpcUserProfilesSensor(coordinator)
    assert sensor.native_value == 2
    first = sensor.extra_state_attributes["profiles"][0]
    assert first["name"] == "Standard Användare"
    assert first["areas"] == [1, 2, 3]
    assert first["doors"] == {"1": "0", "2": "0", "3": "0"}
