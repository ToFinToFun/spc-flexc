"""Translate SPC command failures into Home Assistant service errors."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Any, TypeVar

from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .flexc.connection import FlexCError
from .flexc.flexml import FlexMLError

_T = TypeVar("_T")


async def async_entity_action(action: Awaitable[_T]) -> _T:
    """Run an entity action and expose expected failures to the UI."""
    try:
        return await action
    except HomeAssistantError:
        raise
    except ValueError as err:
        raise ServiceValidationError(str(err)) from err
    except (FlexCError, FlexMLError) as err:
        raise HomeAssistantError("SPC communication failed") from err


async def async_context_user_name(entity: Any) -> str | None:
    """The name of the Home Assistant user behind the entity's current call."""
    context = getattr(entity, "_context", None)
    user_id = getattr(context, "user_id", None)
    if not user_id:
        return None
    user = await entity.hass.auth.async_get_user(user_id)
    return user.name if user is not None else None
