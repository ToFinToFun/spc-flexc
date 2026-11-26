"""Describe SPC panel events in the Home Assistant logbook."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.core import Event, HomeAssistant, callback

from .activity import EVENT_SPC_FLEXC_ACTIVITY
from .bus_events import EVENT_SPC_FLEXC
from .const import DOMAIN


def describe_panel_event(data: dict[str, Any]) -> dict[str, str]:
    """Return the logbook name and message for one ``spc_flexc_event``."""
    name = (
        data.get("door_name") or data.get("zone_name") or data.get("area_name") or "SPC"
    )
    text = data.get("panel_text") or data.get("description")
    if not text:
        text = f"event {data.get('event_id')}"
    if data.get("user_name"):
        text = f"{text} ({data['user_name']})"
    return {"name": str(name), "message": str(text)}


@callback
def async_describe_events(
    hass: HomeAssistant,
    async_describe_event: Callable[[str, str, Callable[[Event], dict[str, str]]], None],
) -> None:
    """Describe ``spc_flexc_event`` entries."""

    @callback
    def _describe(event: Event) -> dict[str, str]:
        return describe_panel_event(dict(event.data))

    async_describe_event(DOMAIN, EVENT_SPC_FLEXC, _describe)

    @callback
    def _describe_activity(event: Event) -> dict[str, str]:
        data = event.data
        message = str(data.get("message") or "")
        user_name = str(data.get("user_name") or "")
        if user_name and user_name not in message:
            message = f"{message} ({user_name})"
        return {"name": str(data.get("title") or "SPC"), "message": message}

    # Panel events are not fired again: they are in the logbook as
    # spc_flexc_event already.
    async_describe_event(DOMAIN, EVENT_SPC_FLEXC_ACTIVITY, _describe_activity)
