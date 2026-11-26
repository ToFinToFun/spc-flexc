"""Services of the SPC FlexC integration."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_register_admin_service

from .const import DOMAIN
from .flexc.calendars import DAYS, SpcCalendarException, parse_periods
from .flexc.connection import FlexCError
from .flexc.flexml import FlexMLError
from .flexc.logs import LOG_KINDS
from .flexc.users import CARD_FLAGS, spc_date, validity_dates
from .flexc.zone_config import (
    KEYARM_FUNCTIONS,
    ZONE_ATTRIBUTES,
    ZONE_NAME_MAX,
    ZONE_TYPES,
    zone_attribute_names,
)

if TYPE_CHECKING:
    from .mapping_gate_coordinator import SpcFlexCMappingGateCoordinator

SERVICE_GET_LOG = "get_log"
SERVICE_SET_CLOCK = "set_clock"
SERVICE_CLEAR_ALERTS = "clear_alerts"
SERVICE_SET_CALENDAR_WEEK = "set_calendar_week"
SERVICE_SET_CALENDAR = "set_calendar"
SERVICE_ADD_CALENDAR = "add_calendar"
SERVICE_DELETE_CALENDAR = "delete_calendar"
SERVICE_ADD_CALENDAR_EXCEPTION = "add_calendar_exception"
SERVICE_EDIT_CALENDAR_EXCEPTION = "edit_calendar_exception"
SERVICE_DELETE_CALENDAR_EXCEPTION = "delete_calendar_exception"
SERVICE_EDIT_USER = "edit_user"
SERVICE_ADD_USER = "add_user"
SERVICE_ASSIGN_UNKNOWN_CARD = "assign_unknown_card"
SERVICE_DELETE_USER = "delete_user"
SERVICE_SET_PIN = "set_pin"
SERVICE_GET_ACTIVITY = "get_activity"
SERVICE_ENABLE_PIN_MANAGEMENT = "enable_pin_management"
SERVICE_DISABLE_PIN_MANAGEMENT = "disable_pin_management"
SERVICE_GET_USER_STATUS = "get_user_status"
SERVICE_GET_UNKNOWN_CARDS = "get_unknown_cards"
SERVICE_EDIT_USER_PROFILE = "edit_user_profile"
SERVICE_ADD_USER_PROFILE = "add_user_profile"
SERVICE_DELETE_USER_PROFILE = "delete_user_profile"
SERVICE_ENGINEER_LOGIN = "engineer_login"
SERVICE_ENGINEER_LOGOUT = "engineer_logout"
SERVICE_SET_ENGINEER_MODE = "set_engineer_mode"
SERVICE_GET_ZONE_CONFIG = "get_zone_config"
SERVICE_EDIT_ZONE = "edit_zone"

ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_LOG = "log"
ATTR_ID = "id"
ATTR_LIMIT = "limit"
ATTR_ATP = "atp"
DEFAULT_LIMIT = 100

GET_LOG_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_LOG): vol.In(sorted(LOG_KINDS)),
        vol.Optional(ATTR_ID): vol.All(vol.Coerce(int), vol.Range(min=1, max=999)),
        vol.Optional(ATTR_ATP): vol.All(vol.Coerce(int), vol.Range(min=1, max=16)),
        vol.Optional(ATTR_LIMIT, default=DEFAULT_LIMIT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=2000)
        ),
    }
)


def _coordinator(
    hass: HomeAssistant, call: ServiceCall
) -> SpcFlexCMappingGateCoordinator:
    """Return the coordinator of the requested (or only) loaded SPC FlexC entry."""
    entries = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]
    entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)
    if entry_id is not None:
        entries = [entry for entry in entries if entry.entry_id == entry_id]
    if not entries:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="no_loaded_entry"
        )
    if len(entries) > 1:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="several_entries"
        )
    return entries[0].runtime_data


async def _async_get_log(hass: HomeAssistant, call: ServiceCall) -> ServiceResponse:
    kind: str = call.data[ATTR_LOG]
    object_id: int | None = call.data.get(ATTR_ID)
    log = LOG_KINDS[kind]
    if log.id_attribute is not None and object_id is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="log_needs_id",
            translation_placeholders={"log": kind},
        )
    coordinator = _coordinator(hass, call)
    try:
        if log.sub_id_attribute is not None:
            records = await coordinator.async_read_log(
                kind, object_id, call.data.get(ATTR_ATP, 1)
            )
        else:
            records = await coordinator.async_read_log(
                kind, object_id if log.id_attribute is not None else None
            )
    except (FlexCError, FlexMLError) as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="log_read_failed",
            translation_placeholders={"log": kind, "error": str(err)},
        ) from err
    entries: list[Any] = records[: call.data[ATTR_LIMIT]]
    return {
        "log": kind,
        "count": len(entries),
        "total": len(records),
        "entries": entries,
    }


PANEL_SCHEMA = vol.Schema({vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string})
ENGINEER_LOGIN_SCHEMA = PANEL_SCHEMA.extend(
    {
        vol.Required("username"): vol.All(cv.string, vol.Length(min=1, max=32)),
        vol.Required("password"): vol.All(cv.string, vol.Length(min=1, max=32)),
        vol.Optional("remember", default=False): cv.boolean,
    }
)
SET_ENGINEER_MODE_SCHEMA = PANEL_SCHEMA.extend({vol.Required("enter"): cv.boolean})

_PROFILES = vol.All(
    cv.ensure_list,
    [vol.All(vol.Coerce(int), vol.Range(min=1, max=255))],
    vol.Length(max=5),
)
_CARD_OPTION_FIELDS: dict[Any, Any] = {
    vol.Optional(option): cv.boolean for option in CARD_FLAGS
}
EDIT_USER_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required("user_id"): vol.All(vol.Coerce(int), vol.Range(min=1, max=9999)),
        vol.Optional("name"): vol.All(cv.string, vol.Length(min=1, max=16)),
        vol.Optional("profiles"): _PROFILES,
        vol.Optional("valid_from"): cv.date,
        vol.Optional("valid_until"): cv.date,
        vol.Optional("no_date_limit"): cv.boolean,
        vol.Optional("card_number"): vol.All(cv.string, vol.Match(r"^\d{1,10}$")),
        vol.Optional("language"): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
        **_CARD_OPTION_FIELDS,
    }
)
ASSIGN_UNKNOWN_CARD_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required("user_id"): vol.All(vol.Coerce(int), vol.Range(min=1, max=9999)),
        vol.Optional("card_index", default=1): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=100)
        ),
    }
)
ADD_USER_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required("user_id"): vol.All(vol.Coerce(int), vol.Range(min=1, max=9999)),
        vol.Required("name"): vol.All(cv.string, vol.Length(min=1, max=16)),
        vol.Required("profiles"): _PROFILES,
        vol.Required("pin"): vol.All(cv.string, vol.Match(r"^\d{4,8}$")),
        vol.Optional("valid_from"): cv.date,
        vol.Optional("valid_until"): cv.date,
        vol.Optional("card_number"): vol.All(cv.string, vol.Match(r"^\d{1,10}$")),
        vol.Optional("language"): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
    }
)
DELETE_USER_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required("user_id"): vol.All(vol.Coerce(int), vol.Range(min=1, max=9999)),
    }
)


async def _async_user_command(hass: HomeAssistant, call: ServiceCall) -> None:
    """Run edit_user, add_user or delete_user; each command is sent once."""
    coordinator = _coordinator(hass, call)
    data = call.data
    try:
        if call.service == SERVICE_EDIT_USER:
            start_date = end_date = None
            if data.get("no_date_limit"):
                start_date, end_date = "0", "0"
            elif "valid_from" in data or "valid_until" in data:
                user = coordinator.data.users.get(data["user_id"])
                start_date, end_date = validity_dates(
                    data.get("valid_from")
                    or spc_date(getattr(user, "start_date", None)),
                    data.get("valid_until")
                    or spc_date(getattr(user, "end_date", None)),
                )
            await coordinator.async_edit_user(
                data["user_id"],
                name=data.get("name"),
                profiles=data.get("profiles"),
                start_date=start_date,
                end_date=end_date,
                card_number=data.get("card_number"),
                card_options={k: data[k] for k in CARD_FLAGS if k in data} or None,
                language=data.get("language"),
            )
        elif call.service == SERVICE_ASSIGN_UNKNOWN_CARD:
            await coordinator.async_assign_unknown_card(
                data["user_id"], data["card_index"]
            )
        elif call.service == SERVICE_ADD_USER:
            start_date, end_date = validity_dates(
                data.get("valid_from"), data.get("valid_until")
            )
            await coordinator.async_add_user(
                data["user_id"],
                data["name"],
                data["profiles"],
                data["pin"],
                start_date,
                end_date,
                data.get("card_number"),
                data.get("language"),
            )
        else:
            await coordinator.async_delete_user(data["user_id"])
    except ValueError as err:
        raise ServiceValidationError(str(err)) from err
    except (FlexCError, FlexMLError) as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="panel_command_failed",
            translation_placeholders={"service": call.service, "error": str(err)},
        ) from err


_PIN = vol.All(cv.string, vol.Match(r"^\d{4,8}$"))
SET_PIN_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required("user_id"): vol.All(vol.Coerce(int), vol.Range(min=1, max=9999)),
        vol.Optional("current_pin"): _PIN,
        vol.Required("pin"): _PIN,
    }
)
ENABLE_PIN_MANAGEMENT_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required("user_id"): vol.All(vol.Coerce(int), vol.Range(min=1, max=9999)),
        vol.Required("pin"): _PIN,
    }
)


async def _async_set_pin(hass: HomeAssistant, call: ServiceCall) -> None:
    """Change a user's PIN; the codes are never logged or stored."""
    coordinator = _coordinator(hass, call)
    try:
        if call.service == SERVICE_ENABLE_PIN_MANAGEMENT:
            await coordinator.async_enable_pin_management(
                call.data["user_id"], call.data["pin"]
            )
        elif call.service == SERVICE_DISABLE_PIN_MANAGEMENT:
            await coordinator.async_disable_pin_management(call.data["user_id"])
        else:
            await coordinator.async_set_pin(
                call.data["user_id"], call.data["pin"], call.data.get("current_pin")
            )
    except ValueError as err:
        raise ServiceValidationError(str(err)) from err
    except (FlexCError, FlexMLError) as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="panel_command_failed",
            translation_placeholders={"service": call.service, "error": str(err)},
        ) from err


GET_ACTIVITY_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Optional(ATTR_LIMIT, default=100): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=2000)
        ),
    }
)


async def _async_get_activity(
    hass: HomeAssistant, call: ServiceCall
) -> ServiceResponse:
    """Return the recent activity: commands, answers, events, log lines."""
    coordinator = _coordinator(hass, call)
    entries: list[Any] = coordinator.activity.recent(call.data[ATTR_LIMIT])
    return {"count": len(entries), "entries": entries}


GET_USER_STATUS_SCHEMA = DELETE_USER_SCHEMA


async def _async_get_user_status(
    hass: HomeAssistant, call: ServiceCall
) -> ServiceResponse:
    """Return one user's status (invalid PIN count, last PIN change, alerts)."""
    coordinator = _coordinator(hass, call)
    try:
        status = await coordinator.async_read_user_status(call.data["user_id"])
    except (FlexCError, FlexMLError) as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="panel_command_failed",
            translation_placeholders={"service": call.service, "error": str(err)},
        ) from err
    return {"user_id": call.data["user_id"], **status}


_ZONE_ID = vol.All(vol.Coerce(int), vol.Range(min=1, max=999))
GET_ZONE_CONFIG_SCHEMA = vol.Schema(
    {vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string, vol.Required("zone_id"): _ZONE_ID}
)
_ZONE_ATTRIBUTE_LIST = vol.All(cv.ensure_list, [vol.In(list(ZONE_ATTRIBUTES))])
EDIT_ZONE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required("zone_id"): _ZONE_ID,
        vol.Optional("name"): vol.All(cv.string, vol.Length(min=1, max=ZONE_NAME_MAX)),
        vol.Optional("type"): vol.All(vol.Coerce(int), vol.In(list(ZONE_TYPES))),
        vol.Optional("area"): vol.All(vol.Coerce(int), vol.Range(min=1, max=64)),
        vol.Optional("technical_delay"): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=9999)
        ),
        vol.Optional("keyarm_function"): vol.All(
            vol.Coerce(int), vol.In(list(KEYARM_FUNCTIONS))
        ),
        vol.Optional("attributes_on"): _ZONE_ATTRIBUTE_LIST,
        vol.Optional("attributes_off"): _ZONE_ATTRIBUTE_LIST,
    }
)


def _zone_config_response(record: dict[str, str]) -> dict[str, Any]:
    """A zone record with its type, attributes and key-arm function by name."""
    zone_type = int(record["TYPE"])
    keyarm = int(record["KEYARM_FUNC"])
    return {
        "zone_id": int(record["ID"]),
        "name": record["NAME"],
        "type": zone_type,
        "type_name": ZONE_TYPES.get(zone_type),
        "area": int(record["AREA"]),
        "attrib": record["ATTRIB"],
        "attributes": zone_attribute_names(record["ATTRIB"]),
        "keyarm_function": keyarm,
        "keyarm_function_name": KEYARM_FUNCTIONS.get(keyarm),
        "technical_delay": int(record["TECHDELAY"]),
    }


async def _async_zone_config(hass: HomeAssistant, call: ServiceCall) -> ServiceResponse:
    """get_zone_config (any user) and edit_zone (admin; engineer + installer mode)."""
    coordinator = _coordinator(hass, call)
    data = call.data
    try:
        if call.service == SERVICE_GET_ZONE_CONFIG:
            record = await coordinator.async_read_zone_config(data["zone_id"])
        else:
            record = await coordinator.async_edit_zone(
                data["zone_id"],
                name=data.get("name"),
                zone_type=data.get("type"),
                area=data.get("area"),
                techdelay=data.get("technical_delay"),
                keyarm_function=data.get("keyarm_function"),
                attributes_on=data.get("attributes_on"),
                attributes_off=data.get("attributes_off"),
            )
    except ValueError as err:
        raise ServiceValidationError(str(err)) from err
    except (FlexCError, FlexMLError) as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="panel_command_failed",
            translation_placeholders={"service": call.service, "error": str(err)},
        ) from err
    return _zone_config_response(record)


async def _async_get_unknown_cards(
    hass: HomeAssistant, call: ServiceCall
) -> ServiceResponse:
    """Return the panel's unknown cards, card numbers masked. UNTESTED."""
    coordinator = _coordinator(hass, call)
    try:
        cards = await coordinator.async_read_unknown_cards()
    except (FlexCError, FlexMLError) as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="panel_command_failed",
            translation_placeholders={"service": call.service, "error": str(err)},
        ) from err
    entries: list[Any] = list(cards)
    return {"count": len(cards), "cards": entries}


_PROFILE_ID = vol.All(vol.Coerce(int), vol.Range(min=1, max=255))
_AREAS = vol.All(cv.ensure_list, [vol.All(vol.Coerce(int), vol.Range(min=1, max=64))])
_CALENDAR = vol.All(vol.Coerce(int), vol.Range(min=0, max=64))
EDIT_USER_PROFILE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required("profile_id"): _PROFILE_ID,
        vol.Optional("name"): vol.All(cv.string, vol.Length(min=1, max=16)),
        vol.Optional("areas"): _AREAS,
        vol.Optional("calendar"): _CALENDAR,
        # {door_id: value}; null removes the door's setting from the profile.
        vol.Optional("doors"): {
            vol.All(vol.Coerce(int), vol.Range(min=1, max=64)): vol.Any(
                None, vol.All(vol.Coerce(str), vol.Match(r"^\d{1,3}$"))
            )
        },
    }
)
ADD_USER_PROFILE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required("profile_id"): _PROFILE_ID,
        vol.Required("name"): vol.All(cv.string, vol.Length(min=1, max=16)),
        vol.Optional("areas", default=[]): _AREAS,
        vol.Optional("calendar", default=0): _CALENDAR,
    }
)
DELETE_USER_PROFILE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required("profile_id"): _PROFILE_ID,
    }
)


async def _async_user_profile_command(hass: HomeAssistant, call: ServiceCall) -> None:
    """Run edit/add/delete_user_profile; each command is sent once. UNTESTED."""
    coordinator = _coordinator(hass, call)
    data = call.data
    try:
        if call.service == SERVICE_EDIT_USER_PROFILE:
            await coordinator.async_edit_user_profile(
                data["profile_id"],
                name=data.get("name"),
                areas=data.get("areas"),
                calendar=data.get("calendar"),
                doors=data.get("doors"),
            )
        elif call.service == SERVICE_ADD_USER_PROFILE:
            await coordinator.async_add_user_profile(
                data["profile_id"], data["name"], data["areas"], data["calendar"]
            )
        else:
            await coordinator.async_delete_user_profile(data["profile_id"])
    except ValueError as err:
        raise ServiceValidationError(str(err)) from err
    except (FlexCError, FlexMLError) as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="panel_command_failed",
            translation_placeholders={"service": call.service, "error": str(err)},
        ) from err


_CALENDAR_WEEK_FIELDS: dict[vol.Marker, Any] = {
    vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
    vol.Required("calendar_id"): vol.All(vol.Coerce(int), vol.Range(min=1, max=64)),
    vol.Required("week_type"): vol.All(vol.Coerce(int), vol.Range(min=1, max=3)),
}
_CALENDAR_WEEK_FIELDS.update({vol.Optional(day.lower()): cv.string for day in DAYS})
SET_CALENDAR_WEEK_SCHEMA = vol.Schema(_CALENDAR_WEEK_FIELDS)


SET_CALENDAR_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required("calendar_id"): vol.All(vol.Coerce(int), vol.Range(min=1, max=64)),
        vol.Optional("name"): vol.All(cv.string, vol.Length(min=1, max=16)),
        vol.Optional("week_types"): vol.All(cv.string, vol.Match(r"^[123]{1,53}$")),
    }
)


_ADD_CALENDAR_FIELDS: dict[vol.Marker, Any] = {
    vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
    vol.Required("calendar_id"): vol.All(vol.Coerce(int), vol.Range(min=1, max=64)),
    vol.Required("name"): vol.All(cv.string, vol.Length(min=1, max=16)),
    vol.Optional("week_types", default="1" * 53): vol.All(
        cv.string, vol.Match(r"^[123]{1,53}$")
    ),
}
# Week type 1 times per day, e.g. "06:00;23:00 09:00;--:--".
_ADD_CALENDAR_FIELDS.update({vol.Optional(day.lower()): cv.string for day in DAYS})
ADD_CALENDAR_SCHEMA = vol.Schema(_ADD_CALENDAR_FIELDS)
DELETE_CALENDAR_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required("calendar_id"): vol.All(vol.Coerce(int), vol.Range(min=1, max=64)),
    }
)


async def _async_calendar_add_delete(hass: HomeAssistant, call: ServiceCall) -> None:
    """Add a calendar (with week type 1 times) or delete one."""
    coordinator = _coordinator(hass, call)
    data = call.data
    try:
        if call.service == SERVICE_ADD_CALENDAR:
            week1 = {}
            for day in DAYS:
                value = data.get(day.lower(), "")
                periods = parse_periods(value)
                if len(periods) != len(value.split()):
                    raise ServiceValidationError(
                        translation_domain=DOMAIN,
                        translation_key="invalid_calendar_times",
                        translation_placeholders={"day": day.lower(), "value": value},
                    )
                week1[day] = periods
            week_types = data["week_types"]
            week_types = week_types + "1" * (53 - len(week_types))
            await coordinator.async_add_calendar(
                data["calendar_id"], data["name"], week_types, {1: week1}
            )
        else:
            await coordinator.async_delete_calendar(data["calendar_id"])
    except ValueError as err:
        raise ServiceValidationError(str(err)) from err
    except (FlexCError, FlexMLError) as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="panel_command_failed",
            translation_placeholders={"service": call.service, "error": str(err)},
        ) from err


_CALENDAR_IDS = vol.All(
    cv.ensure_list,
    [vol.All(vol.Coerce(int), vol.Range(min=1, max=64))],
    vol.Length(min=1),
)
_EXCEPTION_ID = vol.All(vol.Coerce(int), vol.Range(min=1, max=255))
ADD_CALENDAR_EXCEPTION_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Optional("exception_id"): _EXCEPTION_ID,
        vol.Required("name"): vol.All(cv.string, vol.Length(min=1, max=16)),
        vol.Required("start_date"): cv.date,
        vol.Optional("end_date"): cv.date,
        vol.Optional("times", default=""): cv.string,
        vol.Required("calendars"): _CALENDAR_IDS,
    }
)
EDIT_CALENDAR_EXCEPTION_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required("exception_id"): _EXCEPTION_ID,
        vol.Optional("name"): vol.All(cv.string, vol.Length(min=1, max=16)),
        vol.Optional("start_date"): cv.date,
        vol.Optional("end_date"): cv.date,
        vol.Optional("times"): cv.string,
        vol.Optional("calendars"): _CALENDAR_IDS,
    }
)
DELETE_CALENDAR_EXCEPTION_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required("exception_id"): _EXCEPTION_ID,
    }
)


def _exception_periods(value: str) -> tuple[Any, ...]:
    periods = parse_periods(value)
    if len(periods) != len(value.split()):
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_calendar_times",
            translation_placeholders={"day": "times", "value": value},
        )
    return tuple(periods)


async def _async_calendar_exception(hass: HomeAssistant, call: ServiceCall) -> None:
    """Add, change or delete a calendar exception day."""
    coordinator = _coordinator(hass, call)
    data = call.data
    existing = coordinator.data.calendar_exceptions
    try:
        if call.service == SERVICE_DELETE_CALENDAR_EXCEPTION:
            await coordinator.async_delete_calendar_exception(data["exception_id"])
            return
        if call.service == SERVICE_ADD_CALENDAR_EXCEPTION:
            exception_id = data.get("exception_id") or next(
                n for n in range(1, 256) if n not in existing
            )
            exception = SpcCalendarException(
                exception_id=exception_id,
                name=data["name"],
                start=data["start_date"],
                end=data.get("end_date") or data["start_date"],
                periods=_exception_periods(data["times"]),
                calendars=tuple(data["calendars"]),
            )
            await coordinator.async_set_calendar_exception(exception, add=True)
            return
        current = existing.get(data["exception_id"])
        if current is None:
            raise ServiceValidationError(
                f"The panel has no calendar exception {data['exception_id']}"
            )
        exception = replace(
            current,
            name=data.get("name", current.name),
            start=data.get("start_date", current.start),
            end=data.get("end_date", current.end),
            periods=(
                _exception_periods(data["times"])
                if "times" in data
                else current.periods
            ),
            calendars=tuple(data.get("calendars", current.calendars)),
        )
        await coordinator.async_set_calendar_exception(exception, add=False)
    except ValueError as err:
        raise ServiceValidationError(str(err)) from err
    except (FlexCError, FlexMLError) as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="panel_command_failed",
            translation_placeholders={"service": call.service, "error": str(err)},
        ) from err


async def _async_set_calendar(hass: HomeAssistant, call: ServiceCall) -> None:
    """Change a calendar's name and/or week types; the rest is kept."""
    coordinator = _coordinator(hass, call)
    calendar = coordinator.data.calendars.get(call.data["calendar_id"])
    if calendar is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="unknown_calendar",
            translation_placeholders={"calendar_id": str(call.data["calendar_id"])},
        )
    week_types = calendar.week_types
    if "week_types" in call.data:
        # Weeks given replace the first weeks; later weeks keep their type.
        given = call.data["week_types"]
        week_types = given + week_types[len(given) :]
    updated = replace(
        calendar, name=call.data.get("name", calendar.name), week_types=week_types
    )
    try:
        await coordinator.async_set_calendar(updated)
    except (FlexCError, FlexMLError) as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="panel_command_failed",
            translation_placeholders={"service": call.service, "error": str(err)},
        ) from err


async def _async_set_calendar_week(hass: HomeAssistant, call: ServiceCall) -> None:
    """Change given days of one calendar week type; other days are kept."""
    coordinator = _coordinator(hass, call)
    calendar = coordinator.data.calendars.get(call.data["calendar_id"])
    if calendar is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="unknown_calendar",
            translation_placeholders={"calendar_id": str(call.data["calendar_id"])},
        )
    days = {
        day: list(calendar.weeks.get(call.data["week_type"], {}).get(day, []))
        for day in DAYS
    }
    for day in DAYS:
        value = call.data.get(day.lower())
        if value is None:
            continue
        periods = parse_periods(value)
        if len(periods) != len(value.split()):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_calendar_times",
                translation_placeholders={"day": day.lower(), "value": value},
            )
        days[day] = periods
    try:
        await coordinator.async_set_calendar_week(
            call.data["calendar_id"], call.data["week_type"], days
        )
    except (FlexCError, FlexMLError) as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="panel_command_failed",
            translation_placeholders={"service": call.service, "error": str(err)},
        ) from err


async def _async_panel_command(
    hass: HomeAssistant, call: ServiceCall, method: str
) -> None:
    """Run one state-changing panel command once; never retried."""
    coordinator = _coordinator(hass, call)
    try:
        await getattr(coordinator, method)()
    except (FlexCError, FlexMLError) as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="panel_command_failed",
            translation_placeholders={"service": call.service, "error": str(err)},
        ) from err


async def _async_engineer(hass: HomeAssistant, call: ServiceCall) -> None:
    """Engineer login, logout and engineer mode (admin only, sent once)."""
    coordinator = _coordinator(hass, call)
    try:
        if call.service == SERVICE_ENGINEER_LOGIN:
            await coordinator.async_engineer_login(
                call.data["username"], call.data["password"], call.data["remember"]
            )
        elif call.service == SERVICE_ENGINEER_LOGOUT:
            await coordinator.async_engineer_logout()
        else:
            await coordinator.async_set_engineer_mode(call.data["enter"])
    except (FlexCError, FlexMLError) as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="panel_command_failed",
            translation_placeholders={"service": call.service, "error": str(err)},
        ) from err


def async_setup_services(hass: HomeAssistant) -> None:
    """Register the integration's services (once)."""
    if hass.services.has_service(DOMAIN, SERVICE_GET_LOG):
        return

    async def get_log(call: ServiceCall) -> ServiceResponse:
        return await _async_get_log(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_LOG,
        get_log,
        schema=GET_LOG_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )

    async def set_clock(call: ServiceCall) -> None:
        await _async_panel_command(hass, call, "async_set_panel_clock")

    async def clear_alerts(call: ServiceCall) -> None:
        await _async_panel_command(hass, call, "async_clear_all_alerts")

    hass.services.async_register(
        DOMAIN, SERVICE_SET_CLOCK, set_clock, schema=PANEL_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_CLEAR_ALERTS, clear_alerts, schema=PANEL_SCHEMA
    )

    async def engineer(call: ServiceCall) -> None:
        await _async_engineer(hass, call)

    for service, schema in (
        (SERVICE_ENGINEER_LOGIN, ENGINEER_LOGIN_SCHEMA),
        (SERVICE_ENGINEER_LOGOUT, PANEL_SCHEMA),
        (SERVICE_SET_ENGINEER_MODE, SET_ENGINEER_MODE_SCHEMA),
    ):
        async_register_admin_service(hass, DOMAIN, service, engineer, schema=schema)

    async def set_calendar_week(call: ServiceCall) -> None:
        await _async_set_calendar_week(hass, call)

    async def user_command(call: ServiceCall) -> None:
        await _async_user_command(hass, call)

    for service, schema in (
        (SERVICE_EDIT_USER, EDIT_USER_SCHEMA),
        (SERVICE_ADD_USER, ADD_USER_SCHEMA),
        (SERVICE_ASSIGN_UNKNOWN_CARD, ASSIGN_UNKNOWN_CARD_SCHEMA),
        (SERVICE_DELETE_USER, DELETE_USER_SCHEMA),
    ):
        hass.services.async_register(DOMAIN, service, user_command, schema=schema)

    async def set_pin(call: ServiceCall) -> None:
        await _async_set_pin(hass, call)

    for service, schema in (
        (SERVICE_SET_PIN, SET_PIN_SCHEMA),
        (SERVICE_ENABLE_PIN_MANAGEMENT, ENABLE_PIN_MANAGEMENT_SCHEMA),
        (SERVICE_DISABLE_PIN_MANAGEMENT, DELETE_USER_SCHEMA),
    ):
        hass.services.async_register(DOMAIN, service, set_pin, schema=schema)

    async def get_activity(call: ServiceCall) -> ServiceResponse:
        return await _async_get_activity(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_ACTIVITY,
        get_activity,
        schema=GET_ACTIVITY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )

    async def get_user_status(call: ServiceCall) -> ServiceResponse:
        return await _async_get_user_status(hass, call)

    async def get_unknown_cards(call: ServiceCall) -> ServiceResponse:
        return await _async_get_unknown_cards(hass, call)

    for service, handler, schema in (
        (SERVICE_GET_USER_STATUS, get_user_status, GET_USER_STATUS_SCHEMA),
        (SERVICE_GET_UNKNOWN_CARDS, get_unknown_cards, PANEL_SCHEMA),
    ):
        hass.services.async_register(
            DOMAIN,
            service,
            handler,
            schema=schema,
            supports_response=SupportsResponse.ONLY,
        )

    async def zone_config(call: ServiceCall) -> ServiceResponse:
        return await _async_zone_config(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_ZONE_CONFIG,
        zone_config,
        schema=GET_ZONE_CONFIG_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_EDIT_ZONE,
        zone_config,
        schema=EDIT_ZONE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )

    async def user_profile_command(call: ServiceCall) -> None:
        await _async_user_profile_command(hass, call)

    for service, schema in (
        (SERVICE_EDIT_USER_PROFILE, EDIT_USER_PROFILE_SCHEMA),
        (SERVICE_ADD_USER_PROFILE, ADD_USER_PROFILE_SCHEMA),
        (SERVICE_DELETE_USER_PROFILE, DELETE_USER_PROFILE_SCHEMA),
    ):
        hass.services.async_register(
            DOMAIN, service, user_profile_command, schema=schema
        )

    async def set_calendar(call: ServiceCall) -> None:
        await _async_set_calendar(hass, call)

    hass.services.async_register(
        DOMAIN, SERVICE_SET_CALENDAR, set_calendar, schema=SET_CALENDAR_SCHEMA
    )

    async def calendar_add_delete(call: ServiceCall) -> None:
        await _async_calendar_add_delete(hass, call)

    async def calendar_exception(call: ServiceCall) -> None:
        await _async_calendar_exception(hass, call)

    for service, schema in (
        (SERVICE_ADD_CALENDAR_EXCEPTION, ADD_CALENDAR_EXCEPTION_SCHEMA),
        (SERVICE_EDIT_CALENDAR_EXCEPTION, EDIT_CALENDAR_EXCEPTION_SCHEMA),
        (SERVICE_DELETE_CALENDAR_EXCEPTION, DELETE_CALENDAR_EXCEPTION_SCHEMA),
    ):
        hass.services.async_register(DOMAIN, service, calendar_exception, schema=schema)

    for service, schema in (
        (SERVICE_ADD_CALENDAR, ADD_CALENDAR_SCHEMA),
        (SERVICE_DELETE_CALENDAR, DELETE_CALENDAR_SCHEMA),
    ):
        hass.services.async_register(
            DOMAIN, service, calendar_add_delete, schema=schema
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_CALENDAR_WEEK,
        set_calendar_week,
        schema=SET_CALENDAR_WEEK_SCHEMA,
    )
