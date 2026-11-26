"""Validity dates: day numbers, 1 January 2000 = 1 (checked on an SPC4300)."""

from datetime import date

import pytest

from custom_components.spc_flexc.flexc.users import (
    build_add_user_command,
    spc_date,
    spc_day,
    validity_dates,
)


def test_day_numbers_read_on_the_panel() -> None:
    assert spc_day(date(2026, 12, 1)) == "9832"
    assert spc_day(date(2026, 12, 24)) == "9855"
    assert spc_date("9832") == date(2026, 12, 1)
    assert spc_date("0") is None
    assert spc_date(None) is None


def test_validity_period_needs_both_dates_in_order() -> None:
    assert validity_dates(None, None) == ("0", "0")
    assert validity_dates(date(2026, 12, 1), date(2026, 12, 24)) == ("9832", "9855")
    with pytest.raises(ValueError):
        validity_dates(date(2026, 12, 1), None)
    with pytest.raises(ValueError):
        validity_dates(date(2026, 12, 24), date(2026, 12, 1))


def test_add_user_carries_the_dates() -> None:
    command = build_add_user_command(
        97, "Guest", [1], "00000000", "u", "p", "9832", "9855"
    )
    assert 'START_DATE="9832"' in command
    assert 'END_DATE="9855"' in command


def test_card_options_bits_from_the_web_page() -> None:
    from custom_components.spc_flexc.flexc.users import card_attrib_with, card_flags

    assert card_flags("40") == ["card_blocked"]
    assert card_flags("02") == ["extended_time"]
    assert card_flags("3C") == ["pin_bypass", "priority", "escort", "custodian"]
    assert card_attrib_with("00", {"card_blocked": True}) == "40"
    assert card_attrib_with("42", {"card_blocked": False}) == "02"


def test_card_number_and_language_in_the_record() -> None:
    from custom_components.spc_flexc.flexc.users import apply_user_changes

    record = {"USER_ID": "95", "CARD_NO": "0", "CARD_ATTRIB": "00", "LANGUAGE": "255"}
    updated = apply_user_changes(
        record, card_number="12345", card_options={"pin_bypass": True}, language=7
    )
    assert updated["CARD_NO"] == "12345"
    assert updated["CARD_ATTRIB"] == "04"
    assert updated["LANGUAGE"] == "7"
    with pytest.raises(ValueError):
        apply_user_changes(record, card_number="99999999999")


def test_unknown_cards_newest_first_and_assign_by_index() -> None:
    from custom_components.spc_flexc.flexc.users import (
        parse_unknown_cards,
        unknown_card_number,
    )

    reply = (
        '<FLEXML_REPLY VER="1.0"><REPLY_GET_UNKNOWN_CARDS RESULT="0" CMD_RESULT="OK">'
        '<UNKNOWN_CARD DOOR_ID="3" CARD_NO="111" LAST_PRESENTED="09/11/2026 18:24" />'
        '<UNKNOWN_CARD DOOR_ID="1" CARD_NO="222" LAST_PRESENTED="10/11/2026 17:39" />'
        "</REPLY_GET_UNKNOWN_CARDS></FLEXML_REPLY>"
    )
    cards = parse_unknown_cards(reply)
    assert [c["door_id"] for c in cards] == ["1", "3"]
    assert cards[0]["card_no"] == "222"
    assert cards[0]["index"] == "1"
    assert unknown_card_number(reply, 1) == "222"
    with pytest.raises(ValueError):
        unknown_card_number(reply, 3)
