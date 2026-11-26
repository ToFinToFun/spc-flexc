"""Panel calendars: GET_CALENDAR_CONFIG (verified) and EDIT_CALENDAR_WEEK (checked on a panel).

Reply shape seen on an SPC4300 (firmware 3.14.1)::

    <CALENDARS>
      <CALENDAR ID="2" GID="0" NAME="..." WEEK_TYPES="111...1" />
      <CALENDAR_WEEK CALENDAR="2" WEEK="1" SUN="06:00;23:00" MON="..." ... />
      <CALENDAR_WEEK CALENDAR="2" WEEK="2" SUN="" ... />
    </CALENDARS>

``WEEK_TYPES`` has one digit per week of the year (53): the week type (1-3)
that applies that week. Each ``CALENDAR_WEEK`` holds, per week type and day,
space-separated periods ``start;end``. An end of ``--:--`` means the period
has no end time on that day (the panel shows such entries as a single time);
it is treated as a one-minute event. ``24:00`` is the end of the day.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, tzinfo
from xml.sax.saxutils import quoteattr

from .flexml import (
    FlexMLError,
    _build_command_envelope,
    _parse_reply_root,
    _validate_reply,
)

DAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")
NO_TIME = "--:--"


@dataclass(frozen=True)
class CalendarPeriod:
    """One period of a calendar day; ``end`` is None for a single time."""

    start: str
    end: str | None


@dataclass
class SpcCalendar:
    """One panel calendar."""

    calendar_id: int
    name: str
    week_types: str
    gid: str = "0"
    # week type -> day (MON..SUN) -> periods
    weeks: dict[int, dict[str, list[CalendarPeriod]]] = field(default_factory=dict)

    def week_type_for(self, day: date) -> int | None:
        """Return the week type (1-3) that applies to ``day``."""
        week = day.isocalendar().week
        if week > len(self.week_types):
            return None
        try:
            return int(self.week_types[week - 1])
        except ValueError:
            return None

    def periods_for(self, day: date) -> list[CalendarPeriod]:
        """Return the periods of ``day``."""
        week_type = self.week_type_for(day)
        if week_type is None:
            return []
        return self.weeks.get(week_type, {}).get(DAYS[day.weekday()], [])


def parse_periods(value: str) -> list[CalendarPeriod]:
    """Parse ``"06:00;23:00 09:00;--:--"`` into periods; skip malformed ones."""
    periods: list[CalendarPeriod] = []
    for item in value.split():
        start, _, end = item.partition(";")
        if not _valid_time(start):
            continue
        periods.append(CalendarPeriod(start, end if _valid_time(end) else None))
    return periods


def _valid_time(value: str) -> bool:
    if value == NO_TIME or len(value) != 5 or value[2] != ":":
        return False
    hours, minutes = value[:2], value[3:]
    return (
        hours.isdigit()
        and minutes.isdigit()
        and (int(hours) < 24 or value == "24:00")
        and int(minutes) < 60
    )


def period_times(
    day: date, period: CalendarPeriod, timezone: tzinfo
) -> tuple[datetime, datetime]:
    """Return start and end datetimes of a period on ``day``."""

    def at(value: str) -> datetime:
        if value == "24:00":
            return datetime.combine(day + timedelta(days=1), time(0, 0), timezone)
        return datetime.combine(day, time(int(value[:2]), int(value[3:])), timezone)

    start = at(period.start)
    end = at(period.end) if period.end is not None else start + timedelta(minutes=1)
    if end <= start:
        end = start + timedelta(minutes=1)
    return start, end


def build_calendar_config_command(username: str, password: str) -> str:
    """Build CMD_GET_CALENDAR_CONFIG (all calendars)."""
    return _build_command_envelope("<CMD_GET_CALENDAR_CONFIG />", username, password)


def parse_calendar_config(response: str) -> dict[int, SpcCalendar]:
    """Parse REPLY_GET_CALENDAR_CONFIG into calendars by ID."""
    root = _parse_reply_root(response)
    reply = root.find("REPLY_GET_CALENDAR_CONFIG")
    if reply is None:
        raise FlexMLError("REPLY_GET_CALENDAR_CONFIG not found")
    _validate_reply(reply, "REPLY_GET_CALENDAR_CONFIG")
    calendars: dict[int, SpcCalendar] = {}
    for element in reply.iter("CALENDAR"):
        try:
            calendar_id = int(element.get("ID", ""))
        except ValueError:
            continue
        calendars[calendar_id] = SpcCalendar(
            calendar_id=calendar_id,
            name=element.get("NAME", "").strip(),
            week_types=element.get("WEEK_TYPES", ""),
            gid=element.get("GID", "0"),
        )
    for element in reply.iter("CALENDAR_WEEK"):
        try:
            calendar_id = int(element.get("CALENDAR", ""))
            week_type = int(element.get("WEEK", ""))
        except ValueError:
            continue
        calendar = calendars.get(calendar_id)
        if calendar is None:
            continue
        calendar.weeks[week_type] = {
            day: parse_periods(element.get(day, "")) for day in DAYS
        }
    return calendars


def format_periods(periods: list[CalendarPeriod]) -> str:
    """Format periods the way the panel sends them."""
    return " ".join(f"{p.start};{p.end or NO_TIME}" for p in periods)


def build_edit_calendar_week_command(
    calendar_id: int,
    week_type: int,
    days: dict[str, list[CalendarPeriod]],
    username: str,
    password: str,
) -> str:
    """Build CMD_EDIT_CALENDAR_WEEK (checked on an SPC4300).

    All seven days are always sent, so the panel never fills in days it was
    not given. Raises ValueError for a bad week type or time.
    """
    if week_type not in (1, 2, 3):
        raise ValueError("Week type must be 1, 2 or 3")
    attributes = []
    for day in ("SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"):
        periods = days.get(day, [])
        for period in periods:
            if not _valid_time(period.start) or (
                period.end is not None and not _valid_time(period.end)
            ):
                raise ValueError(f"Invalid time in {day}: {period}")
        attributes.append(f"{day}={quoteattr(format_periods(periods))}")
    return _build_command_envelope(
        f'<CMD_EDIT_CALENDAR_WEEK CALENDAR="{int(calendar_id)}" WEEK="{week_type}" '
        + " ".join(attributes)
        + " />",
        username,
        password,
    )


def build_edit_calendar_command(
    calendar: SpcCalendar, username: str, password: str
) -> str:
    """Build CMD_EDIT_CALENDAR for a whole calendar record (checked on an SPC4300).

    The attributes mirror the CALENDAR element of GET_CALENDAR_CONFIG: ID,
    GID, NAME and WEEK_TYPES (one digit 1-3 per week, 53 weeks).
    """
    if not calendar.week_types or any(c not in "123" for c in calendar.week_types):
        raise ValueError("WEEK_TYPES must be digits 1-3")
    if len(calendar.week_types) > 53:
        raise ValueError("WEEK_TYPES has at most 53 weeks")
    if not calendar.name or len(calendar.name) > 16:
        raise ValueError("A calendar name has 1-16 characters")
    return _build_command_envelope(
        f'<CMD_EDIT_CALENDAR ID="{int(calendar.calendar_id)}" '
        f"GID={quoteattr(calendar.gid)} NAME={quoteattr(calendar.name)} "
        f"WEEK_TYPES={quoteattr(calendar.week_types)} />",
        username,
        password,
    )


def build_add_calendar_command(
    calendar_id: int, name: str, week_types: str, username: str, password: str
) -> str:
    """Build CMD_ADD_CALENDAR (same attributes as EDIT_CALENDAR).

    The reference panel allows at most 4 calendars; the web interface gives a
    new calendar the first free number.
    """
    if not name or len(name) > 16:
        raise ValueError("A calendar name has 1-16 characters")
    if (
        not week_types
        or any(c not in "123" for c in week_types)
        or len(week_types) > 53
    ):
        raise ValueError("WEEK_TYPES must be 1-53 digits 1-3")
    return _build_command_envelope(
        f'<CMD_ADD_CALENDAR ID="{int(calendar_id)}" GID="0" NAME={quoteattr(name)} '
        f"WEEK_TYPES={quoteattr(week_types)} />",
        username,
        password,
    )


def build_delete_calendar_command(
    calendar_id: int, username: str, password: str
) -> str:
    """Build CMD_DELETE_CALENDAR (ID only)."""
    return _build_command_envelope(
        f'<CMD_DELETE_CALENDAR ID="{int(calendar_id)}" />', username, password
    )


# Exception days (checked on an SPC4300, 3.14.1, 2026-11-10). One
# CALENDAR_EXCEPT element per exception in GET_CALENDAR_CONFIG:
#   ID, GID, NAME, START and END (DDMMYY), TIMES (periods like the week days,
#   at most 4), CALENDARS (16 hex digits; byte n-1 from the left holds
#   calendars 8(n-1)+1..8n, lowest bit first: "0D00..." = calendars 1, 3, 4).
# ADD_CALEX and EDIT_CALEX take the same attributes, DELETE_CALEX only ID.
MAX_EXCEPTION_PERIODS = 4


@dataclass(frozen=True)
class SpcCalendarException:
    """One exception day or period, shared by one or more calendars."""

    exception_id: int
    name: str
    start: date
    end: date
    periods: tuple[CalendarPeriod, ...]
    calendars: tuple[int, ...]
    gid: str = "0"


def calendars_from_mask(mask: str) -> tuple[int, ...]:
    """Return the calendar IDs in a CALENDARS mask."""
    ids = []
    for index in range(0, len(mask) - 1, 2):
        try:
            byte = int(mask[index : index + 2], 16)
        except ValueError:
            return ()
        ids += [index // 2 * 8 + bit + 1 for bit in range(8) if byte & (1 << bit)]
    return tuple(ids)


def mask_from_calendars(calendars: list[int]) -> str:
    """Return the 16-hex-digit CALENDARS mask for calendar IDs 1-64."""
    data = bytearray(8)
    for calendar_id in calendars:
        if not 1 <= int(calendar_id) <= 64:
            raise ValueError(f"Calendar {calendar_id} is outside 1-64")
        data[(int(calendar_id) - 1) // 8] |= 1 << ((int(calendar_id) - 1) % 8)
    return data.hex().upper()


def _panel_date(value: str) -> date | None:
    try:
        return datetime.strptime(value.strip(), "%d%m%y").date()
    except ValueError:
        return None


def parse_calendar_exceptions(response: str) -> dict[int, SpcCalendarException]:
    """Parse the CALENDAR_EXCEPT elements of REPLY_GET_CALENDAR_CONFIG."""
    root = _parse_reply_root(response)
    reply = root.find("REPLY_GET_CALENDAR_CONFIG")
    if reply is None:
        raise FlexMLError("REPLY_GET_CALENDAR_CONFIG not found")
    exceptions: dict[int, SpcCalendarException] = {}
    for element in reply.iter("CALENDAR_EXCEPT"):
        try:
            exception_id = int(element.get("ID", ""))
        except ValueError:
            continue
        start = _panel_date(element.get("START", ""))
        end = _panel_date(element.get("END", ""))
        if start is None or end is None:
            continue
        exceptions[exception_id] = SpcCalendarException(
            exception_id=exception_id,
            name=element.get("NAME", "").strip(),
            start=start,
            end=end,
            periods=tuple(parse_periods(element.get("TIMES", ""))),
            calendars=calendars_from_mask(element.get("CALENDARS", "")),
            gid=element.get("GID", "0"),
        )
    return exceptions


def build_calendar_exception_command(
    exception: SpcCalendarException, add: bool, username: str, password: str
) -> str:
    """Build CMD_ADD_CALEX or CMD_EDIT_CALEX for a whole exception."""
    if not exception.name or len(exception.name) > 16:
        raise ValueError("An exception name has 1-16 characters")
    if exception.end < exception.start:
        raise ValueError("The end date is before the start date")
    if len(exception.periods) > MAX_EXCEPTION_PERIODS:
        raise ValueError(f"An exception has at most {MAX_EXCEPTION_PERIODS} periods")
    for period in exception.periods:
        if not _valid_time(period.start) or (
            period.end is not None and not _valid_time(period.end)
        ):
            raise ValueError(f"Invalid time: {period}")
    if not exception.calendars:
        raise ValueError("An exception needs at least one calendar")
    command = "ADD_CALEX" if add else "EDIT_CALEX"
    return _build_command_envelope(
        f'<CMD_{command} ID="{int(exception.exception_id)}" '
        f"GID={quoteattr(exception.gid)} NAME={quoteattr(exception.name)} "
        f'START="{exception.start:%d%m%y}" END="{exception.end:%d%m%y}" '
        f"TIMES={quoteattr(format_periods(list(exception.periods)))} "
        f'CALENDARS="{mask_from_calendars(list(exception.calendars))}" />',
        username,
        password,
    )


def build_delete_calendar_exception_command(
    exception_id: int, username: str, password: str
) -> str:
    """Build CMD_DELETE_CALEX (ID only)."""
    return _build_command_envelope(
        f'<CMD_DELETE_CALEX ID="{int(exception_id)}" />', username, password
    )
