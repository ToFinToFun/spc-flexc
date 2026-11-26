"""Entity IDs built from the panel's numbers, never from names.

An entity ID is set once, when the entity is first registered, and Home
Assistant does not change it when a name changes. IDs built from names would
go stale after a rename in the panel (and mix languages), so every entity
suggests ``<domain>.spc_<what>_<number>_<function>`` from its unique ID:
``binary_sensor.spc_zone_25``, ``switch.spc_zone_25_inhibition``,
``button.spc_door_3_lock``, ``alarm_control_panel.spc_area_1``. The display
name still comes from the panel and follows it.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from typing import Any

from homeassistant.util import slugify

# Unique-ID suffixes that read better shortened in an entity ID.
_REWRITES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^zone_(\d+)_motion$"), r"zone_\1"),
    (re.compile(r"^door_(\d+)_door_"), r"door_\1_"),
    (re.compile(r"^panel_alarm$"), "alarm"),
)


def object_id(entry_id: str, unique_id: str) -> str:
    """Return the suggested object ID (``spc_...``) for a unique ID."""
    suffix = unique_id.removeprefix(f"{entry_id}_")
    for pattern, replacement in _REWRITES:
        suffix = pattern.sub(replacement, suffix)
    return f"spc_{slugify(suffix)}"


def with_spc_entity_ids(
    domain: str, entry_id: str, add_entities: Callable[..., Any]
) -> Callable[..., Any]:
    """Wrap async_add_entities so each new entity suggests its spc_ ID."""

    def add(entities: Iterable[Any], *args: Any, **kwargs: Any) -> Any:
        entities = list(entities)
        for entity in entities:
            unique_id = getattr(entity, "unique_id", None)
            if getattr(entity, "entity_id", None) is None and unique_id:
                entity.entity_id = f"{domain}.{object_id(entry_id, unique_id)}"
        return add_entities(entities, *args, **kwargs)

    return add
