"""Panel users: no secrets in state, read-modify-write EDIT_USER, services."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.spc_flexc.coordinator import SpcFlexCCoordinator
from custom_components.spc_flexc.flexc.users import (
    apply_user_changes,
    build_add_user_command,
    build_delete_user_command,
    build_edit_user_command,
    parse_user_records,
    public_user,
)
from custom_components.spc_flexc.models import SpcState
from custom_components.spc_flexc.sensor import SpcUsersSensor

# Field set of a real SPC4300 (3.14.1) record; values are placeholders.
RECORD = (
    '<USER_CONFIG USER_ID="{id}" GID="0" NAME="{name}" PIN="1A2B3C4D" CARD_NO="{card}" '
    'CARD_ATTRIB="00" USER_ATTRIB="0" START_DATE="0" END_DATE="0" LANGUAGE="7" '
    'USER_PROFILE_1="1" USER_PROFILE_2="2" USER_PROFILE_3="0" USER_PROFILE_4="0" '
    'USER_PROFILE_5="0" WEBPASS_DATA="SECRETWEB" />'
)
REPLY = (
    '<FLEXML_REPLY VER="1.0"><REPLY_GET_USER_CONFIG RESULT="0" CMD_RESULT="OK">'
    + RECORD.format(id=7, name="Guest", card="00012345")
    + RECORD.format(id=8, name="Child", card="")
    + "</REPLY_GET_USER_CONFIG></FLEXML_REPLY>"
)
# PIN and web password stay hidden; card numbers are shown (owner 2026-11-11).
SECRETS = ("1A2B3C4D", "SECRETWEB")


def test_public_user_has_no_secrets() -> None:
    records = parse_user_records(REPLY)
    users = [public_user(record) for record in records]
    assert users[0].name == "Guest"
    assert users[0].profiles == (1, 2)
    assert users[0].has_card is True
    assert users[1].has_card is False
    assert "PIN" not in users[0].raw_fields
    assert users[0].card_number == "12345"
    assert users[1].card_number is None
    assert not any(secret in repr(users) for secret in SECRETS)


def test_edit_user_keeps_secrets_unchanged_and_drops_web_password() -> None:
    record = parse_user_records(REPLY)[0]
    updated = apply_user_changes(record, name="Guest 2", profiles=[3])
    command = build_edit_user_command(updated, "u", "p")
    assert '<CMD_EDIT_USER USER_ID="7"' in command
    assert 'NAME="Guest 2"' in command
    assert 'USER_PROFILE_1="3"' in command and 'USER_PROFILE_2="0"' in command
    assert 'PIN="1A2B3C4D"' in command
    assert 'CARD_NO="00012345"' in command
    assert "WEBPASS_DATA" not in command
    assert record["NAME"] == "Guest"


def test_apply_user_changes_validation() -> None:
    record = parse_user_records(REPLY)[0]
    with pytest.raises(ValueError):
        apply_user_changes(record, name="")
    with pytest.raises(ValueError):
        apply_user_changes(record, name="x" * 17)
    with pytest.raises(ValueError):
        apply_user_changes(record, profiles=[1, 2, 3, 4, 5, 6])
    dates = apply_user_changes(record, start_date="01012027", end_date="31012027")
    assert (dates["START_DATE"], dates["END_DATE"]) == ("01012027", "31012027")


def test_add_and_delete_user_commands() -> None:
    add = build_add_user_command(20, "Guest", [6], "12345639", "u", "p")
    assert '<CMD_ADD_USER USER_ID="20" NAME="Guest" PIN="12345639" CARD_NO="0"' in add
    assert 'LANGUAGE="255"' in add and 'USER_PROFILE_1="6"' in add
    assert "GID" not in add and "WEBPASS_DATA" not in add
    assert '<CMD_DELETE_USER USER_ID="20" />' in build_delete_user_command(20, "u", "p")


def _coordinator() -> MagicMock:
    coordinator = MagicMock(spec=SpcFlexCCoordinator)
    coordinator._client_operation_lock = asyncio.Lock()
    coordinator.client = MagicMock()
    coordinator.client.command_username = "u"
    coordinator.client.command_password = "p"
    coordinator.client.async_ensure_connected = AsyncMock()
    coordinator.state = SpcState()
    coordinator._async_read_users_locked = AsyncMock()
    coordinator._async_save_config_locked = AsyncMock()
    coordinator._pin_keys = {}
    coordinator._store_pin_keys = MagicMock()
    coordinator._key_for = lambda *a: SpcFlexCCoordinator._key_for(coordinator, *a)
    coordinator._mark_pin_set = lambda uid: SpcFlexCCoordinator._mark_pin_set(
        coordinator, uid
    )
    return coordinator


@pytest.mark.asyncio
async def test_edit_user_reads_record_then_sends_once() -> None:
    coordinator = _coordinator()
    coordinator._async_read_user_record_locked = AsyncMock(
        return_value=parse_user_records(REPLY)[0]
    )
    coordinator.client.async_send_flexml = AsyncMock(
        return_value='<FLEXML_REPLY VER="1.0"><REPLY_EDIT_USER RESULT="0" CMD_RESULT="OK"/></FLEXML_REPLY>'
    )
    await SpcFlexCCoordinator.async_edit_user(coordinator, 7, profiles=[1])
    coordinator._async_read_user_record_locked.assert_awaited_once_with(7)
    coordinator.client.async_send_flexml.assert_awaited_once()
    sent = coordinator.client.async_send_flexml.call_args.args[0]
    assert 'USER_PROFILE_1="1"' in sent and 'USER_PROFILE_2="0"' in sent
    coordinator._async_save_config_locked.assert_awaited_once()
    coordinator._async_read_users_locked.assert_awaited_once_with(force=True)


def test_users_sensor_has_no_secrets() -> None:
    coordinator = MagicMock()
    coordinator.entry.entry_id = "test"
    coordinator.entry.data = {"host": "192.0.2.1"}
    users = {u.user_id: u for u in map(public_user, parse_user_records(REPLY))}
    coordinator.data = SpcState(users=users)
    sensor = SpcUsersSensor(coordinator)
    assert sensor.native_value == 2
    attrs = sensor.extra_state_attributes
    assert attrs["users"][0]["name"] == "Guest"
    assert not any(secret in repr(attrs) for secret in SECRETS)


@pytest.mark.asyncio
async def test_save_config_is_sent_and_checked() -> None:
    coordinator = _coordinator()
    coordinator.client.async_send_flexml = AsyncMock(
        return_value='<FLEXML_REPLY VER="1.0"><REPLY_SAVE_CONFIG RESULT="0" CMD_RESULT="OK"/></FLEXML_REPLY>'
    )
    await SpcFlexCCoordinator._async_save_config_locked(coordinator)
    assert (
        "<CMD_SAVE_CONFIG />" in coordinator.client.async_send_flexml.call_args.args[0]
    )


@pytest.mark.asyncio
async def test_add_user_saves_config() -> None:
    coordinator = _coordinator()
    coordinator.client.async_send_flexml = AsyncMock(
        return_value='<FLEXML_REPLY VER="1.0"><REPLY_ADD_USER RESULT="0" CMD_RESULT="OK"/></FLEXML_REPLY>'
    )
    await SpcFlexCCoordinator._async_send_panel_command(
        coordinator, "<cmd/>", "ADD_USER", save=True
    )
    coordinator._async_save_config_locked.assert_awaited_once()


def test_recode_pin_uses_the_users_key() -> None:
    from custom_components.spc_flexc.flexc.users import recode_pin

    # Made-up key 5A5A1234: PIN 0000 is stored as the key, 1357 as key ^ 0x54D.
    assert recode_pin("5A5A1234", "0000", "1357") == "5A5A1779"
    assert recode_pin("5A5A1779", "1357", "0000") == "5A5A1234"
    with pytest.raises(ValueError):
        recode_pin("5A5A1234", "12", "1357")


@pytest.mark.asyncio
async def test_set_pin_edits_saves_and_reads_back() -> None:
    coordinator = _coordinator()
    record = parse_user_records(REPLY)[0] | {"PIN": "5A5A1234"}
    coordinator._async_read_user_record_locked = AsyncMock(
        side_effect=[dict(record), record | {"PIN": "5A5A1779"}]
    )
    coordinator.client.async_send_flexml = AsyncMock(
        return_value='<FLEXML_REPLY VER="1.0"><REPLY_EDIT_USER RESULT="0" CMD_RESULT="OK"/></FLEXML_REPLY>'
    )
    await SpcFlexCCoordinator.async_set_pin(coordinator, 7, "1357", "0000")
    sent = coordinator.client.async_send_flexml.call_args.args[0]
    assert 'PIN="5A5A1779"' in sent and "WEBPASS_DATA" not in sent
    coordinator._async_save_config_locked.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_pin_fails_when_read_back_differs() -> None:
    from custom_components.spc_flexc.flexc.flexml import FlexMLError

    coordinator = _coordinator()
    record = parse_user_records(REPLY)[0] | {"PIN": "5A5A1234"}
    coordinator._async_read_user_record_locked = AsyncMock(
        side_effect=[dict(record), dict(record)]
    )
    coordinator.client.async_send_flexml = AsyncMock(
        return_value='<FLEXML_REPLY VER="1.0"><REPLY_EDIT_USER RESULT="0" CMD_RESULT="OK"/></FLEXML_REPLY>'
    )
    with pytest.raises(FlexMLError):
        await SpcFlexCCoordinator.async_set_pin(coordinator, 7, "1357", "0000")


def test_pin_key_and_encode() -> None:
    from custom_components.spc_flexc.flexc.users import encode_pin, pin_key

    assert pin_key("12345639", "0065") == "12345678"
    assert encode_pin("12345678", "0065") == "12345639"


@pytest.mark.asyncio
async def test_pin_management_lifecycle() -> None:
    coordinator = _coordinator()
    record = parse_user_records(REPLY)[0] | {"PIN": "5A5A1779"}
    coordinator._async_read_user_record_locked = AsyncMock(return_value=dict(record))
    await SpcFlexCCoordinator.async_enable_pin_management(coordinator, 7, "1357")
    assert coordinator._pin_keys[7] == {
        "key": "5A5A1234",
        "confirmed": False,
        "pending": False,
    }
    assert SpcFlexCCoordinator.pin_management(coordinator, 7) == "unconfirmed"
    # A keypad login before HA set a PIN proves nothing.
    SpcFlexCCoordinator._confirm_pin_key(coordinator, 7)
    assert coordinator._pin_keys[7]["confirmed"] is False
    # set_pin without the current PIN uses the stored key.
    coordinator._async_read_user_record_locked = AsyncMock(
        side_effect=[dict(record), record | {"PIN": "5A5A1230"}]
    )
    coordinator.client.async_send_flexml = AsyncMock(
        return_value='<FLEXML_REPLY VER="1.0"><REPLY_EDIT_USER RESULT="0" CMD_RESULT="OK"/></FLEXML_REPLY>'
    )
    await SpcFlexCCoordinator.async_set_pin(coordinator, 7, "0004")
    assert 'PIN="5A5A1230"' in coordinator.client.async_send_flexml.call_args.args[0]
    assert coordinator._pin_keys[7]["pending"] is True
    assert SpcFlexCCoordinator.pin_management(coordinator, 7) == "pending"
    SpcFlexCCoordinator._confirm_pin_key(coordinator, 7)
    assert SpcFlexCCoordinator.pin_management(coordinator, 7) == "confirmed"
    assert SpcFlexCCoordinator.pin_managed_numbers(coordinator) == {7: "confirmed"}
    await SpcFlexCCoordinator.async_disable_pin_management(coordinator, 7)
    assert SpcFlexCCoordinator.pin_management(coordinator, 7) is None


@pytest.mark.asyncio
async def test_set_pin_without_key_or_current_pin_is_refused() -> None:
    coordinator = _coordinator()
    coordinator._async_read_user_record_locked = AsyncMock(
        return_value=parse_user_records(REPLY)[0]
    )
    with pytest.raises(ValueError):
        await SpcFlexCCoordinator.async_set_pin(coordinator, 7, "0004")


@pytest.mark.asyncio
async def test_add_user_needs_a_stored_key() -> None:
    coordinator = _coordinator()
    with pytest.raises(ValueError):
        await SpcFlexCCoordinator.async_add_user(coordinator, 65, "Guest", [6], "0065")
    coordinator._pin_keys[65] = {"key": "12345678", "confirmed": True, "pending": False}
    coordinator._async_send_panel_command = AsyncMock()
    await SpcFlexCCoordinator.async_add_user(coordinator, 65, "Guest", [6], "0065")
    command = coordinator._async_send_panel_command.call_args.args[0]
    assert 'PIN="12345639"' in command
    assert coordinator._async_send_panel_command.call_args.kwargs == {"save": True}


def test_pin_confirmed_by_door_entry_only_without_a_card() -> None:
    """A guest without areas confirms the PIN at a door (owner 2026-11-14)."""
    from types import SimpleNamespace

    coordinator = _coordinator()
    coordinator._pin_keys = {
        15: {"key": "x", "confirmed": False, "pending": True},
        95: {"key": "y", "confirmed": False, "pending": True},
    }
    coordinator.state.users = {
        15: SimpleNamespace(has_card=False),
        95: SimpleNamespace(has_card=True),
    }
    coordinator._confirm_pin_key = lambda user_id: SpcFlexCCoordinator._confirm_pin_key(
        coordinator, user_id
    )
    SpcFlexCCoordinator._confirm_pin_from_event(coordinator, 3000, 95)
    assert coordinator._pin_keys[95]["confirmed"] is False  # may have been the card
    SpcFlexCCoordinator._confirm_pin_from_event(coordinator, 3000, 15)
    assert coordinator._pin_keys[15]["confirmed"] is True
    SpcFlexCCoordinator._confirm_pin_from_event(coordinator, 4003, 95)
    assert coordinator._pin_keys[95]["confirmed"] is True
