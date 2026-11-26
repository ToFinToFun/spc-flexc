"""Panel calendars: parsing, events, the calendar entity and set_calendar_week."""

from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import ServiceValidationError

from custom_components.spc_flexc.calendar import SpcCalendarEntity, calendar_events
from custom_components.spc_flexc.flexc.calendars import (
    CalendarPeriod,
    build_edit_calendar_week_command,
    parse_calendar_config,
    parse_periods,
    period_times,
)
from custom_components.spc_flexc.models import SpcState
from custom_components.spc_flexc.services import (
    SET_CALENDAR_WEEK_SCHEMA,
    _async_set_calendar_week,
)

TZ = ZoneInfo("Europe/Stockholm")
WEEK_TYPES = "1" * 10 + "2" + "1" * 42
# Shape of a real SPC4300 (firmware 3.14.1) reply; names are placeholders.
REPLY = (
    '<FLEXML_REPLY VER="1.0"><REPLY_GET_CALENDAR_CONFIG RESULT="0" CMD_RESULT="OK"><CALENDARS>'
    f'<CALENDAR ID="2" GID="0" NAME="Daytime" WEEK_TYPES="{WEEK_TYPES}" />'
    '<CALENDAR_WEEK CALENDAR="2" WEEK="1" SUN="06:00;23:00" MON="06:00;23:00" '
    'TUE="12:00;23:59 05:45;12:00" WED="" THU="" FRI="" SAT="23:00;--:-- 24:00;--:--" />'
    '<CALENDAR_WEEK CALENDAR="2" WEEK="2" SUN="" MON="08:00;09:00" TUE="" WED="" '
    'THU="" FRI="" SAT="" />'
    "</CALENDARS></REPLY_GET_CALENDAR_CONFIG></FLEXML_REPLY>"
)


def test_parse_calendar_config() -> None:
    calendars = parse_calendar_config(REPLY)
    calendar = calendars[2]
    assert calendar.name == "Daytime"
    assert calendar.weeks[1]["MON"] == [CalendarPeriod("06:00", "23:00")]
    assert calendar.weeks[1]["TUE"] == [
        CalendarPeriod("12:00", "23:59"),
        CalendarPeriod("05:45", "12:00"),
    ]
    assert calendar.weeks[1]["SAT"] == [
        CalendarPeriod("23:00", None),
        CalendarPeriod("24:00", None),
    ]
    assert calendar.weeks[1]["WED"] == []


def test_week_type_and_periods_for_date() -> None:
    calendar = parse_calendar_config(REPLY)[2]
    week_11_monday = date.fromisocalendar(2026, 11, 1)
    assert calendar.week_type_for(week_11_monday) == 2
    assert calendar.periods_for(week_11_monday) == [CalendarPeriod("08:00", "09:00")]
    assert calendar.periods_for(date.fromisocalendar(2026, 12, 1)) == [
        CalendarPeriod("06:00", "23:00")
    ]


def test_parse_periods_skips_bad_values() -> None:
    assert parse_periods("06:00;23:00 99:00;10:00 xx 07:00;--:--") == [
        CalendarPeriod("06:00", "23:00"),
        CalendarPeriod("07:00", None),
    ]


def test_period_times() -> None:
    day = date(2026, 11, 10)
    start, end = period_times(day, CalendarPeriod("23:00", "24:00"), TZ)
    assert end == datetime(2026, 11, 11, 0, 0, tzinfo=TZ)
    start, end = period_times(day, CalendarPeriod("09:15", None), TZ)
    assert end - start == timedelta(minutes=1)


def test_calendar_events_in_range() -> None:
    calendar = parse_calendar_config(REPLY)[2]
    monday = date.fromisocalendar(2026, 12, 1)
    start = datetime.combine(monday, datetime.min.time(), TZ)
    events = calendar_events(calendar, start, start + timedelta(days=2))
    assert [(e.start.hour, e.end.hour) for e in events] == [(6, 23), (5, 12), (12, 23)]


def test_calendar_entity() -> None:
    coordinator = MagicMock()
    coordinator.entry.entry_id = "test"
    coordinator.data = SpcState(calendars=parse_calendar_config(REPLY))
    entity = SpcCalendarEntity(coordinator, 2)
    assert entity.unique_id == "test_calendar_2"
    assert entity.translation_key == "calendar"
    assert entity._attr_translation_placeholders["calendar_name"] == "Daytime"
    assert entity.available is True
    assert SpcCalendarEntity(coordinator, 9).available is False


def test_edit_calendar_week_command() -> None:
    command = build_edit_calendar_week_command(
        2,
        1,
        {"MON": [CalendarPeriod("06:00", "23:00"), CalendarPeriod("07:00", None)]},
        "u",
        "p",
    )
    assert '<CMD_EDIT_CALENDAR_WEEK CALENDAR="2" WEEK="1" SUN=""' in command
    assert 'MON="06:00;23:00 07:00;--:--"' in command
    with pytest.raises(ValueError):
        build_edit_calendar_week_command(2, 4, {}, "u", "p")
    with pytest.raises(ValueError):
        build_edit_calendar_week_command(
            2, 1, {"MON": [CalendarPeriod("25:00", None)]}, "u", "p"
        )


def _hass(coordinator) -> MagicMock:
    entry = MagicMock(
        entry_id="abc", state=ConfigEntryState.LOADED, runtime_data=coordinator
    )
    hass = MagicMock()
    hass.config_entries.async_entries.return_value = [entry]
    return hass


@pytest.mark.asyncio
async def test_set_calendar_week_keeps_days_not_given() -> None:
    coordinator = MagicMock()
    coordinator.data = SpcState(calendars=parse_calendar_config(REPLY))
    coordinator.async_set_calendar_week = AsyncMock()
    call = MagicMock(
        data=SET_CALENDAR_WEEK_SCHEMA(
            {"calendar_id": 2, "week_type": 1, "mon": "07:00;22:00", "wed": ""}
        ),
        service="set_calendar_week",
    )
    await _async_set_calendar_week(_hass(coordinator), call)
    _, _, days = coordinator.async_set_calendar_week.await_args.args
    assert days["MON"] == [CalendarPeriod("07:00", "22:00")]
    assert days["SUN"] == [CalendarPeriod("06:00", "23:00")]
    assert days["WED"] == []


@pytest.mark.asyncio
async def test_set_calendar_week_validation() -> None:
    coordinator = MagicMock()
    coordinator.data = SpcState(calendars=parse_calendar_config(REPLY))
    hass = _hass(coordinator)
    bad_time = MagicMock(
        data=SET_CALENDAR_WEEK_SCHEMA(
            {"calendar_id": 2, "week_type": 1, "mon": "7:00-22"}
        )
    )
    with pytest.raises(ServiceValidationError):
        await _async_set_calendar_week(hass, bad_time)
    unknown = MagicMock(
        data=SET_CALENDAR_WEEK_SCHEMA({"calendar_id": 9, "week_type": 1})
    )
    with pytest.raises(ServiceValidationError):
        await _async_set_calendar_week(hass, unknown)


def test_edit_calendar_command() -> None:
    from dataclasses import replace

    from custom_components.spc_flexc.flexc.calendars import build_edit_calendar_command

    calendar = parse_calendar_config(REPLY)[2]
    command = build_edit_calendar_command(calendar, "u", "p")
    assert '<CMD_EDIT_CALENDAR ID="2" GID="0" NAME="Daytime" WEEK_TYPES="' in command
    with pytest.raises(ValueError):
        build_edit_calendar_command(replace(calendar, week_types="1x"), "u", "p")
    with pytest.raises(ValueError):
        build_edit_calendar_command(replace(calendar, name=""), "u", "p")


@pytest.mark.asyncio
async def test_set_calendar_keeps_weeks_not_given() -> None:
    from custom_components.spc_flexc.services import (
        SET_CALENDAR_SCHEMA,
        _async_set_calendar,
    )

    coordinator = MagicMock()
    coordinator.data = SpcState(calendars=parse_calendar_config(REPLY))
    coordinator.async_set_calendar = AsyncMock()
    call = MagicMock(
        data=SET_CALENDAR_SCHEMA({"calendar_id": 2, "week_types": "333"}),
        service="set_calendar",
    )
    await _async_set_calendar(_hass(coordinator), call)
    updated = coordinator.async_set_calendar.await_args.args[0]
    assert updated.week_types == "333" + WEEK_TYPES[3:]
    assert updated.name == "Daytime"


def test_non_ascii_names_are_sent_as_character_references() -> None:
    from dataclasses import replace

    from custom_components.spc_flexc.flexc.calendars import build_edit_calendar_command

    calendar = replace(parse_calendar_config(REPLY)[2], name="Barn tillträde")
    command = build_edit_calendar_command(calendar, "u", "p")
    command.encode("ascii")
    assert 'NAME="Barn tilltr&#228;de"' in command


@pytest.mark.asyncio
async def test_set_calendar_sends_the_week_times_back_before_saving() -> None:
    import asyncio
    from unittest.mock import AsyncMock, MagicMock

    from custom_components.spc_flexc.coordinator import SpcFlexCCoordinator
    from custom_components.spc_flexc.flexc.calendars import (
        CalendarPeriod,
        SpcCalendar,
    )

    coordinator = MagicMock(spec=SpcFlexCCoordinator)
    coordinator.state = MagicMock()
    coordinator._client_operation_lock = asyncio.Lock()
    coordinator.client = MagicMock()
    coordinator.client.command_username = "u"
    coordinator.client.command_password = "p"
    coordinator.client.async_ensure_connected = AsyncMock()

    def reply(command: str) -> str:
        name = (
            "EDIT_CALENDAR_WEEK"
            if "CMD_EDIT_CALENDAR_WEEK" in command
            else "EDIT_CALENDAR"
        )
        return f'<FLEXML_REPLY VER="1.0"><REPLY_{name} RESULT="0" CMD_RESULT="OK"/></FLEXML_REPLY>'

    coordinator.client.async_send_flexml = AsyncMock(side_effect=reply)
    calendar = SpcCalendar(
        2,
        "Kids",
        "1" * 53,
        weeks={1: {"MON": [CalendarPeriod("06:00", "23:00")]}},
    )
    await SpcFlexCCoordinator.async_set_calendar(coordinator, calendar)
    sent = [c.args[0] for c in coordinator.client.async_send_flexml.call_args_list]
    assert "<CMD_EDIT_CALENDAR " in sent[0]
    assert [s.count("<CMD_EDIT_CALENDAR_WEEK ") for s in sent[1:]] == [1, 1, 1]
    assert 'WEEK="1"' in sent[1] and 'MON="06:00;23:00"' in sent[1]
    assert 'WEEK="3"' in sent[3] and 'MON=""' in sent[3]
    coordinator._async_save_config_locked.assert_awaited_once()


def test_add_and_delete_calendar_commands() -> None:
    from custom_components.spc_flexc.flexc.calendars import (
        build_add_calendar_command,
        build_delete_calendar_command,
    )

    add = build_add_calendar_command(4, "Lås", "1" * 53, "u", "p")
    assert '<CMD_ADD_CALENDAR ID="4" GID="0" NAME="L&#229;s"' in add
    assert '<CMD_DELETE_CALENDAR ID="4" />' in build_delete_calendar_command(
        4, "u", "p"
    )
    with pytest.raises(ValueError):
        build_add_calendar_command(4, "", "1", "u", "p")


CALEX_REPLY = (
    '<FLEXML_REPLY VER="1.0"><REPLY_GET_CALENDAR_CONFIG RESULT="0" CMD_RESULT="OK">'
    "<CALENDARS>"
    '<CALENDAR ID="1" GID="0" NAME="A" WEEK_TYPES="1" />'
    '<CALENDAR_EXCEPT ID="1" GID="0" NAME="Holiday" START="010127" END="020127" '
    'TIMES="13:00;14:00" CALENDARS="0D00000000000000" />'
    "</CALENDARS></REPLY_GET_CALENDAR_CONFIG></FLEXML_REPLY>"
)


def test_calendar_exceptions_round_trip() -> None:
    from datetime import date

    from custom_components.spc_flexc.flexc.calendars import (
        build_calendar_exception_command,
        build_delete_calendar_exception_command,
        calendars_from_mask,
        mask_from_calendars,
        parse_calendar_exceptions,
    )

    assert calendars_from_mask("0D00000000000000") == (1, 3, 4)
    assert mask_from_calendars([1, 3, 4]) == "0D00000000000000"
    assert mask_from_calendars([9]) == "0001000000000000"
    exception = parse_calendar_exceptions(CALEX_REPLY)[1]
    assert exception.name == "Holiday"
    assert (exception.start, exception.end) == (date(2027, 1, 1), date(2027, 1, 2))
    assert exception.calendars == (1, 3, 4)
    edit = build_calendar_exception_command(exception, False, "u", "p")
    assert (
        '<CMD_EDIT_CALEX ID="1" GID="0" NAME="Holiday" START="010127" END="020127" '
        'TIMES="13:00;14:00" CALENDARS="0D00000000000000" />'
    ) in edit
    assert "<CMD_ADD_CALEX " in build_calendar_exception_command(
        exception, True, "u", "p"
    )
    assert '<CMD_DELETE_CALEX ID="1" />' in build_delete_calendar_exception_command(
        1, "u", "p"
    )


def test_exception_times_replace_week_times() -> None:
    from datetime import date, datetime

    from homeassistant.util import dt as dt_util

    from custom_components.spc_flexc.calendar import calendar_events
    from custom_components.spc_flexc.flexc.calendars import (
        CalendarPeriod,
        SpcCalendar,
        SpcCalendarException,
    )

    week = {
        day: [CalendarPeriod("06:00", "23:00")]
        for day in ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")
    }
    calendar = SpcCalendar(2, "Kids", "1" * 53, weeks={1: week})
    holiday = SpcCalendarException(
        1,
        "Holiday",
        date(2027, 1, 1),
        date(2027, 1, 1),
        (CalendarPeriod("13:00", "14:00"),),
        (2,),
    )
    other = SpcCalendarException(
        2, "Other", date(2027, 1, 2), date(2027, 1, 2), (), (3,)
    )
    tz = dt_util.get_default_time_zone()
    events = calendar_events(
        calendar,
        datetime(2027, 1, 1, tzinfo=tz),
        datetime(2027, 1, 3, tzinfo=tz),
        [holiday, other],
    )
    assert [(e.start.hour, e.end.hour, e.summary) for e in events] == [
        (13, 14, "Kids: Holiday"),
        (6, 23, "Kids"),
    ]
