"""Panel calendars (GET_CALENDAR_CONFIG) as Home Assistant calendars (read-only)."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .coordinator import SpcFlexCCoordinator
from .entity_ids import with_spc_entity_ids
from .flexc.calendars import SpcCalendar, SpcCalendarException, period_times
from .flexc.device import build_panel_device_info

LOOKAHEAD_DAYS = 7


def calendar_events(
    calendar: SpcCalendar,
    start: datetime,
    end: datetime,
    exceptions: list[SpcCalendarException] | None = None,
) -> list[CalendarEvent]:
    """Return the calendar's periods that overlap ``start``..``end``.

    On a day covered by an exception of this calendar, the exception's times
    replace the week times (an exception with no times means no period).
    """
    timezone = start.tzinfo or dt_util.get_default_time_zone()
    mine = [e for e in exceptions or [] if calendar.calendar_id in e.calendars]
    events: list[CalendarEvent] = []
    day = (start - timedelta(days=1)).astimezone(timezone).date()
    last = end.astimezone(timezone).date()
    while day <= last:
        exception = next((e for e in mine if e.start <= day <= e.end), None)
        periods = calendar.periods_for(day) if exception is None else exception.periods
        for period in periods:
            period_start, period_end = period_times(day, period, timezone)
            if period_end > start and period_start < end:
                if exception is not None:
                    summary = f"{calendar.name}: {exception.name}"
                else:
                    summary = calendar.name
                events.append(
                    CalendarEvent(
                        start=period_start,
                        end=period_end,
                        summary=summary,
                        description=None
                        if period.end
                        else "Single time (no end time in the panel calendar)",
                    )
                )
        day += timedelta(days=1)
    return sorted(events, key=lambda event: event.start)


class SpcCalendarEntity(CoordinatorEntity[SpcFlexCCoordinator], CalendarEntity):
    """One SPC calendar."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SpcFlexCCoordinator, calendar_id: int) -> None:
        super().__init__(coordinator)
        self.calendar_id = calendar_id
        self._attr_unique_id = f"{coordinator.entry.entry_id}_calendar_{calendar_id}"
        self._attr_device_info = build_panel_device_info(coordinator)
        self._attr_translation_key = "calendar"
        self._set_name()

    def _calendar(self) -> SpcCalendar | None:
        return self.coordinator.data.calendars.get(self.calendar_id)

    def _set_name(self) -> None:
        calendar = self._calendar()
        self._attr_translation_placeholders = {
            "calendar_id": str(self.calendar_id),
            "calendar_name": calendar.name if calendar and calendar.name else "",
        }

    @property
    def available(self) -> bool:
        return self._calendar() is not None

    @property
    def event(self) -> CalendarEvent | None:
        calendar = self._calendar()
        if calendar is None:
            return None
        now = dt_util.now()
        events = calendar_events(
            calendar, now, now + timedelta(days=LOOKAHEAD_DAYS), self._exceptions()
        )
        return events[0] if events else None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        calendar = self._calendar()
        if calendar is None:
            return {}
        return {
            "calendar_id": self.calendar_id,
            "calendar_name": calendar.name,
            "week_type_now": calendar.week_type_for(dt_util.now().date()),
            # Week type (1-3) of ISO weeks 1-53, as the panel keeps it.
            "week_types": calendar.week_types,
            # Week type -> day -> "HH:MM;HH:MM" periods (end "--:--" = none),
            # the format set_calendar_week takes.
            "weeks": {
                str(week_type): {
                    day.lower(): " ".join(
                        f"{p.start};{p.end or '--:--'}" for p in periods
                    )
                    for day, periods in days.items()
                }
                for week_type, days in sorted(calendar.weeks.items())
            },
            "exceptions": [
                {
                    "exception_id": exception.exception_id,
                    "name": exception.name,
                    "start": exception.start.isoformat(),
                    "end": exception.end.isoformat(),
                    "times": " ".join(
                        f"{p.start};{p.end or '--:--'}" for p in exception.periods
                    ),
                    "calendars": sorted(exception.calendars),
                }
                for exception in sorted(
                    self.coordinator.data.calendar_exceptions.values(),
                    key=lambda e: e.start,
                )
                if self.calendar_id in exception.calendars
            ],
        }

    async def async_get_events(
        self, hass, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        calendar = self._calendar()
        if calendar is None:
            return []
        return calendar_events(calendar, start_date, end_date, self._exceptions())

    def _exceptions(self) -> list[SpcCalendarException]:
        return list(self.coordinator.data.calendar_exceptions.values())


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Add one calendar entity per panel calendar."""
    async_add_entities = with_spc_entity_ids(
        "calendar", entry.entry_id, async_add_entities
    )
    coordinator: SpcFlexCCoordinator = entry.runtime_data
    known: set[int] = set()

    def add_calendars() -> None:
        new = [cid for cid in coordinator.data.calendars if cid not in known]
        known.update(new)
        if new:
            async_add_entities(SpcCalendarEntity(coordinator, cid) for cid in new)

    add_calendars()
    entry.async_on_unload(coordinator.async_add_listener(add_calendars))
