"""Door events carry the panel's own names (from its complete event table)."""

from custom_components.spc_flexc.flexc.event_table import (
    EVENT_TABLE,
    event_description,
)
from custom_components.spc_flexc.sensor import FLEXC_EVENT_DESCRIPTIONS


def test_door_event_names_are_the_panels_own() -> None:
    """Door events 3000-3016, as the SPC4300 lists them (firmware 3.14.1)."""
    expected = {
        3000: ("Entry Granted", "Inpassage godkänd"),
        3001: ("Entry Denied", None),
        3006: ("Door Forced Open", None),
        3010: ("Door Open", None),
        3011: ("Door Closed", None),
        3012: ("Door Release", None),
        3014: ("Unknown card", None),
    }
    for event_id, (english, swedish) in expected.items():
        assert event_description(event_id, "en") == english
        assert FLEXC_EVENT_DESCRIPTIONS[event_id] == english
        if swedish is not None:
            assert event_description(event_id, "sv") == swedish
    assert all(event_id in EVENT_TABLE for event_id in range(3000, 3017))


def test_event_table_language_and_unknown_ids() -> None:
    assert event_description(None) is None
    assert event_description(99999, "sv") is None
    assert event_description(3502, "sv-SE") == "Deltillkoppling A"
    assert event_description(3502, "fr") == "Partset A"
    assert len(EVENT_TABLE) == 608
